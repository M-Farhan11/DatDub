"""Semantic checks on a schema before it reaches the engine.

Pydantic checks shapes; this module checks meaning: references exist, types
fit each rule kind, bounds are finite and ordered, keys and FKs make sense,
scenarios target something they can change, and the request fits the
resource limits. Used by `/generate` (user-edited schemas) and by the AI
output validator, so both paths accept exactly the same things.
"""

import math
from collections.abc import Iterable

import pandas as pd
from faker.config import AVAILABLE_LOCALES

from app.core.exceptions import InvalidSchema, RowsLimitExceeded
from app.schemas import DatasetSchema, GenerateRequest, Rule, ScenarioProposal, TableSchema
from app.schemas.dataset import ColumnSchema

MAX_TABLES = 30
MAX_COLUMNS = 100
MAX_CHILDREN = 1000
MAX_SCENARIOS = 20
MAX_SEED = 2**32 - 1

_NUMERIC = ("integer", "float", "decimal")
_TEMPORAL = ("date", "datetime")


# --- schema --------------------------------------------------------------------


def schema_problems(schema: DatasetSchema) -> list[str]:
    problems: list[str] = []
    if not schema.tables:
        return ["The schema has no tables."]
    if len(schema.tables) > MAX_TABLES:
        problems.append(f"At most {MAX_TABLES} tables are supported.")
    problems += [f"Duplicate table name '{n}'." for n in _dupes(t.name for t in schema.tables)]

    for t in schema.tables:
        if not t.columns:
            problems.append(f"Table '{t.name}' has no columns.")
            continue
        if len(t.columns) > MAX_COLUMNS:
            problems.append(f"Table '{t.name}' has more than {MAX_COLUMNS} columns.")
        problems += [f"Duplicate column '{t.name}.{n}'." for n in _dupes(c.name for c in t.columns)]
        if _col(t, t.primary_key) is None:
            problems.append(f"Primary key '{t.name}.{t.primary_key}' is not a column of the table.")
        for c in t.columns:
            problems += _column_problems(t, c)
        for fk in t.foreign_keys:
            problems += _fk_problems(schema, t, fk)
    if _has_cycle(schema):
        problems.append("Foreign keys form a cycle; the generator needs parents before children.")

    problems += [f"Duplicate rule id '{i}'." for i in _dupes(r.id for r in schema.rules)]
    for rule in schema.rules:
        problem = rule_problem(rule, schema)
        if problem:
            problems.append(f"Rule {rule.id} ({rule.kind} on {rule.table}.{rule.column}): {problem}.")
    return problems


def _column_problems(t: TableSchema, c: ColumnSchema) -> list[str]:
    where = f"{t.name}.{c.name}"
    out: list[str] = []
    if c.data_type in _NUMERIC:
        lo, hi = _finite(c.min), _finite(c.max)
        if (c.min is not None and lo is None) or (c.max is not None and hi is None):
            out.append(f"{where}: min/max must be finite numbers.")
        elif lo is not None and hi is not None and lo > hi:
            out.append(f"{where}: min is greater than max.")
    elif c.data_type in _TEMPORAL:
        lo, hi = _date(c.min), _date(c.max)
        if (c.min not in (None, "") and lo is None) or (c.max not in (None, "") and hi is None):
            out.append(f"{where}: min/max must be dates (YYYY-MM-DD).")
        elif lo is not None and hi is not None and lo > hi:
            out.append(f"{where}: min is after max.")
    if c.allowed_values is not None and not c.allowed_values:
        out.append(f"{where}: allowed_values is empty.")
    p = c.profile
    if p is not None:
        if p.histogram and not all(
            _finite(a) is not None and _finite(b) is not None and a <= b and n >= 0 for a, b, n in p.histogram
        ):
            out.append(f"{where}: the profile histogram has invalid bins.")
        if p.top_values and not all(_finite(f) is not None and 0 <= f <= 1 for _, f in p.top_values):
            out.append(f"{where}: the profile frequencies must be between 0 and 1.")
        if _finite(p.mean) is None and p.mean is not None or _finite(p.std) is None and p.std is not None:
            out.append(f"{where}: the profile mean/std must be finite.")
    return out


def _fk_problems(schema: DatasetSchema, t: TableSchema, fk) -> list[str]:
    where = f"Foreign key {t.name}.{fk.column}"
    parent = schema.table(fk.ref_table)
    if _col(t, fk.column) is None:
        return [f"{where}: no such column."]
    if parent is None:
        return [f"{where}: unknown table '{fk.ref_table}'."]
    if parent.name == t.name:
        return [f"{where}: self-references are not supported."]
    if _col(parent, fk.ref_column) is None:
        return [f"{where}: '{fk.ref_table}.{fk.ref_column}' does not exist."]
    out = []
    if fk.min_children > fk.max_children:
        out.append(f"{where}: min_children is greater than max_children.")
    if fk.max_children > MAX_CHILDREN:
        out.append(f"{where}: max_children is at most {MAX_CHILDREN}.")
    dist = fk.children_distribution
    if dist is not None and (
        not all(n >= 0 and _finite(f) is not None and f >= 0 for n, f in dist) or sum(f for _, f in dist) <= 0
    ):
        out.append(f"{where}: children_distribution must have non-negative counts and frequencies.")
    return out


def _has_cycle(schema: DatasetSchema) -> bool:
    parents = {t.name: {fk.ref_table for fk in t.foreign_keys if fk.ref_table != t.name} for t in schema.tables}
    state: dict[str, int] = {}  # 1 = visiting, 2 = done

    def visit(name: str) -> bool:
        if state.get(name) == 1:
            return True
        if state.get(name) == 2 or name not in parents:
            return False
        state[name] = 1
        if any(visit(p) for p in parents[name]):
            return True
        state[name] = 2
        return False

    return any(visit(n) for n in parents)


# --- rules ---------------------------------------------------------------------


def rule_problem(rule: Rule, schema: DatasetSchema) -> str | None:
    """Why the engine cannot enforce/check `rule` on `schema`, or None."""
    t = schema.table(rule.table)
    col = _col(t, rule.column) if t else None
    if col is None:
        return "unknown table or column"
    p = rule.params

    if rule.kind == "range":
        lo, hi = _finite(p.get("min")), _finite(p.get("max"))
        if col.data_type not in _NUMERIC:
            return "range needs a numeric column"
        if lo is None and hi is None or (p.get("min") is not None and lo is None) or (p.get("max") is not None and hi is None):
            return "range needs finite min and/or max"
        if lo is not None and hi is not None and lo > hi:
            return "min is greater than max"
    elif rule.kind == "allowed_values":
        if not isinstance(p.get("values"), list) or not p["values"]:
            return "allowed_values needs a non-empty list of values"
    elif rule.kind == "date_order":
        after = _col(t, p.get("after") or rule.column)
        if col.data_type not in _TEMPORAL or after is None or after.data_type not in _TEMPORAL:
            return "date_order needs date columns"
        if after.name != col.name:
            return "`after` must be the rule's own column"
        source = t
        if p.get("via_fk"):
            fk = next((f for f in t.foreign_keys if f.column == p["via_fk"]), None)
            source = schema.table(fk.ref_table) if fk else None
            if source is None:
                return f"via_fk '{p['via_fk']}' is not a foreign key of {t.name}"
        before = _col(source, p.get("before"))
        if before is None or before.data_type not in _TEMPORAL:
            return f"unknown date column '{p.get('before')}'"
    elif rule.kind == "sum_of_children":
        child = schema.table(p.get("child_table") or "")
        if child is None or not any(fk.ref_table == t.name for fk in child.foreign_keys):
            return "child table is not linked by a foreign key"
        parts = [x.strip() for x in str(p.get("expr") or "").split("*")]
        if not 1 <= len(parts) <= 2 or any((c := _col(child, x)) is None or c.data_type not in _NUMERIC for x in parts):
            return f"expression '{p.get('expr')}' must use one or two numeric columns of {child.name}"
        if col.data_type not in _NUMERIC:
            return "the total column must be numeric"
    elif rule.kind == "lte_parent":
        parent = schema.table(p.get("parent_table") or "")
        if parent is None or not any(fk.ref_table == parent.name for fk in t.foreign_keys):
            return "parent table is not linked by a foreign key"
        pcol = _col(parent, p.get("parent_column"))
        if pcol is None or pcol.data_type not in _NUMERIC or col.data_type not in _NUMERIC:
            return "lte_parent needs numeric columns on both sides"
    return None


# --- scenarios -----------------------------------------------------------------


def proposal_problem(p: ScenarioProposal, schema: DatasetSchema) -> str | None:
    """Why the injector cannot run this scenario on `schema`, or None.

    null_burst may target any non-key column: on a required column the NULLs
    are an intended nullability violation (reported as expected)."""
    t = schema.table(p.table)
    if t is None:
        return f"unknown table '{p.table}'"
    keys = {t.primary_key, *(fk.column for fk in t.foreign_keys)}
    col = _col(t, p.column) if p.column else None
    if p.kind in ("null_burst", "extreme_value", "boundary_date"):
        if col is None:
            return "needs an existing column"
        if col.name in keys:
            return "cannot target a key column"
        if p.kind == "extreme_value" and col.data_type not in _NUMERIC:
            return "extreme_value needs a numeric column"
        if p.kind == "boundary_date" and col.data_type not in _TEMPORAL:
            return "boundary_date needs a date column"
    elif p.kind == "rule_violation":
        rule = next((r for r in schema.rules if r.id == p.rule_id), None)
        if rule is None or rule.table != p.table:
            return f"unknown rule '{p.rule_id}' on {p.table}"
    return None


# --- generate request ------------------------------------------------------------


def check_generate_request(req: GenerateRequest, row_cap: int, max_total_cells: int) -> None:
    """Raise a 422 unless the request can be generated exactly as asked."""
    schema = req.schema_
    problems = schema_problems(schema)
    if problems:
        raise InvalidSchema(_join(problems))

    roots = {t.name for t in schema.tables if not t.foreign_keys}
    for name, n in req.rows.items():
        if schema.table(name) is None:
            problems.append(f"rows: unknown table '{name}'.")
        elif name not in roots:
            problems.append(f"rows: '{name}' is a child table; its row count follows its parent.")
        elif n < 1:
            problems.append(f"rows: '{name}' needs at least 1 row.")
    if not 0 <= req.seed <= MAX_SEED:
        problems.append(f"seed must be between 0 and {MAX_SEED}.")
    if req.locale not in AVAILABLE_LOCALES:
        problems.append(f"Unknown locale '{req.locale[:20]}'. Use a Faker locale such as en_US or de_DE.")
    if len(req.scenarios) > MAX_SCENARIOS:
        problems.append(f"At most {MAX_SCENARIOS} scenarios per generation.")
    problems += [f"Duplicate scenario id '{i}'." for i in _dupes(s.proposal.id for s in req.scenarios)]
    for sel in req.scenarios:
        problem = proposal_problem(sel.proposal, schema)
        if problem:
            problems.append(f"Scenario {sel.proposal.id} ({sel.proposal.kind}): {problem}.")
    if problems:
        raise InvalidSchema(_join(problems))

    too_big = {t: n for t, n in req.rows.items() if n > row_cap}
    if too_big:
        raise RowsLimitExceeded(f"Max {row_cap:,} rows per table. Requested: {too_big}")
    cells = estimate_cells(schema, req.rows, row_cap)
    if cells > max_total_cells:
        raise RowsLimitExceeded(
            f"This request would generate about {cells:,} cells (rows × columns across all tables); "
            f"the limit is {max_total_cells:,}. Lower the row counts."
        )


def estimate_cells(schema: DatasetSchema, rows: dict[str, int], row_cap: int) -> int:
    """Expected rows × columns over all tables, following the mean children per parent."""
    from app.engine.generator import DEFAULT_ROOT_ROWS, topological_order

    order = topological_order(schema)
    depth = {t.name: i for i, t in enumerate(order)}
    counts: dict[str, float] = {}
    for t in order:
        fks = [fk for fk in t.foreign_keys if fk.ref_table in counts]
        driver = max(fks, key=lambda fk: depth[fk.ref_table], default=None)
        if driver is None:
            n = rows[t.name] if t.name in rows else (t.row_count_hint or DEFAULT_ROOT_ROWS)
        else:
            n = counts[driver.ref_table] * _mean_children(driver)
        counts[t.name] = min(float(n), row_cap)
    return int(sum(counts[t.name] * len(t.columns) for t in schema.tables))


def _mean_children(fk) -> float:
    lo, hi = fk.min_children, max(fk.min_children, fk.max_children)
    if fk.cardinality == "1:1":
        hi = min(hi, 1)
    if fk.children_distribution:
        total = sum(f for _, f in fk.children_distribution)
        if total > 0:
            return sum(min(max(n, lo), hi) * f for n, f in fk.children_distribution) / total
    return (lo + hi) / 2


# --- helpers ---------------------------------------------------------------------


def _col(t: TableSchema | None, name) -> ColumnSchema | None:
    return next((c for c in t.columns if c.name == name), None) if t and name else None


def _dupes(names: Iterable[str]) -> list[str]:
    seen, dupes = set(), []
    for n in names:
        if n in seen and n not in dupes:
            dupes.append(n)
        seen.add(n)
    return dupes


def _finite(value) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _date(value):
    try:
        ts = pd.Timestamp(str(value))
    except (ValueError, TypeError):
        return None
    return None if pd.isna(ts) else ts


def _join(problems: list[str]) -> str:
    more = f" (+{len(problems) - 5} more)" if len(problems) > 5 else ""
    return " ".join(problems[:5]) + more
