"""Infer catalogue rules inside the source database (schema + sample mode).

Samples of different tables are independent, so a rule such as "invoice
total = sum of its items" cannot be checked on them. Instead every candidate
rule is checked over the WHOLE table with one aggregate query that returns
only counts (violations / rows). No rows leave the database; everything runs
in the read-only transaction with the statement timeout.

A rule is kept only when it holds for every row that has values. Kinds:
allowed_values (verifies the sampled categories are complete), date_order
(same table and through an FK), sum_of_children and lte_parent.
"""

import itertools
import logging

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from app.ingest.db_guard import map_db_error
from app.ingest.rules import MIN_ROWS, _dedupe_sums
from app.schemas.dataset import ColumnSchema, DatasetSchema, Rule, TableSchema

logger = logging.getLogger("app.ingest.db")

MAX_QUERIES = 60
_NUMERIC = ("integer", "float", "decimal")
_TEMPORAL = ("date", "datetime")
_MONEY_TOL = 0.011

# (child table, fk column) -> (parent table, referenced column) as declared in the database
DbLinks = dict[tuple[str, str], tuple[str, str]]


class _Budget:
    def __init__(self) -> None:
        self.left = MAX_QUERIES
        self.skipped = 0


def infer_db_rules(c: Connection, schema_name: str | None, schema: DatasetSchema, links: DbLinks) -> tuple[list[Rule], list[str]]:
    rules: list[Rule] = []
    notes: list[str] = []
    budget = _Budget()
    q = _Quoter(c, schema_name)

    def add(kind: str, table: str, column: str, params: dict, description: str) -> None:
        rules.append(Rule(id=f"r{len(rules) + 1}", kind=kind, table=table, column=column, params=params, description=description))

    for t in schema.tables:
        keys = _keys(t)
        for col in t.columns:
            if col.allowed_values and col.name not in keys:
                bad = _scalar(c, budget, f"SELECT COUNT(*) FROM {q.t(t.name)} WHERE {q.c(col.name)} IS NOT NULL "
                              f"AND CAST({q.c(col.name)} AS TEXT) NOT IN :vals", vals=col.allowed_values)
                if bad == 0:
                    add("allowed_values", t.name, col.name, {"values": col.allowed_values},
                        f"{t.name}.{col.name} is one of {', '.join(col.allowed_values)}")
                elif bad is not None:
                    col.allowed_values = None  # the sample missed some values: not a closed list

        dates = [col.name for col in t.columns if col.data_type in _TEMPORAL and col.name not in keys]
        for a, b in itertools.combinations(dates, 2):
            row = _row(c, budget, f"SELECT SUM(CASE WHEN {q.c(a)} > {q.c(b)} THEN 1 ELSE 0 END), "
                                  f"SUM(CASE WHEN {q.c(a)} < {q.c(b)} THEN 1 ELSE 0 END), COUNT(*) "
                                  f"FROM {q.t(t.name)} WHERE {q.c(a)} IS NOT NULL AND {q.c(b)} IS NOT NULL")
            order = _order(row)
            if order:
                first, second = (a, b) if order == "<=" else (b, a)
                add("date_order", t.name, second, {"before": first, "after": second}, f"{t.name}.{first} is on or before {second}")

    for child in schema.tables:
        for fk in child.foreign_keys:
            parent = schema.table(fk.ref_table)
            link = links.get((child.name, fk.column))
            if parent is None or link is None:
                continue
            join = (f"FROM {q.t(child.name)} ch JOIN {q.t(parent.name)} pa "
                    f"ON ch.{q.c(fk.column)} = pa.{q.c(link[1])}")
            _via_fk_dates(c, budget, q, child, parent, fk.column, join, add)
            _sums(c, budget, q, child, parent, fk.column, link[1], add)
            _caps(c, budget, q, child, parent, join, add)

    if budget.skipped:
        notes.append(f"Skipped {budget.skipped} rule check(s) (query limit or timeout).")
    rules = _dedupe_sums(rules)
    if rules:
        notes.append(f"Found {len(rules)} rule(s) that hold for every row in the database (checked with aggregate queries).")
    return rules, notes


def _via_fk_dates(c, budget, q, child: TableSchema, parent: TableSchema, fk_col: str, join: str, add) -> None:
    """parent date <= child date through the FK (customer created -> invoice issued)."""
    p_dates = [col.name for col in parent.columns if col.data_type in _TEMPORAL and col.name not in _keys(parent)]
    c_dates = [col.name for col in child.columns if col.data_type in _TEMPORAL and col.name not in _keys(child)]
    for pc, cc in itertools.product(p_dates, c_dates):
        row = _row(c, budget, f"SELECT SUM(CASE WHEN pa.{q.c(pc)} > ch.{q.c(cc)} THEN 1 ELSE 0 END), "
                              f"SUM(CASE WHEN pa.{q.c(pc)} < ch.{q.c(cc)} THEN 1 ELSE 0 END), COUNT(*) {join} "
                              f"WHERE pa.{q.c(pc)} IS NOT NULL AND ch.{q.c(cc)} IS NOT NULL")
        if _order(row) == "<=":
            add("date_order", child.name, cc, {"before": pc, "after": cc, "via_fk": fk_col},
                f"{child.name}.{cc} is on or after {parent.name}.{pc}")


def _sums(c, budget, q, child: TableSchema, parent: TableSchema, fk_col: str, ref_col: str, add) -> None:
    """parent column = SUM(child expr) per parent, over the whole table."""
    targets = [col.name for col in parent.columns if _is_money(col) and col.name not in _keys(parent)]
    nums = [col for col in child.columns if col.data_type in _NUMERIC and col.name not in _keys(child)]
    exprs = [[col.name] for col in nums if _is_money(col)]
    exprs += [[a.name, b.name] for a, b in itertools.permutations(nums, 2)
              if a.semantic_type == "quantity" and _is_money(b)]
    for target in targets:
        for parts in exprs:
            expr = " * ".join(f"{q.c(p)}" for p in parts)
            row = _row(c, budget,
                       f"SELECT COUNT(*), SUM(CASE WHEN ABS(COALESCE(s.v, 0) - pa.{q.c(target)}) > {_MONEY_TOL} THEN 1 ELSE 0 END), "
                       f"SUM(CASE WHEN s.v IS NOT NULL THEN 1 ELSE 0 END) "
                       f"FROM {q.t(parent.name)} pa LEFT JOIN (SELECT {q.c(fk_col)} AS k, SUM({expr}) AS v "
                       f"FROM {q.t(child.name)} GROUP BY {q.c(fk_col)}) s ON s.k = pa.{q.c(ref_col)} "
                       f"WHERE pa.{q.c(target)} IS NOT NULL")
            if row and (row[0] or 0) >= MIN_ROWS and row[1] == 0 and (row[2] or 0) > 0:
                expr_text = " * ".join(parts)
                add("sum_of_children", parent.name, target, {"child_table": child.name, "expr": expr_text},
                    f"{parent.name}.{target} equals the sum of {child.name} {expr_text}")
                break


def _caps(c, budget, q, child: TableSchema, parent: TableSchema, join: str, add) -> None:
    """child money <= parent money through the FK (payment <= invoice total)."""
    for cc in [col.name for col in child.columns if _is_money(col) and col.name not in _keys(child)]:
        for pc in [col.name for col in parent.columns if _is_money(col) and col.name not in _keys(parent)]:
            row = _row(c, budget, f"SELECT SUM(CASE WHEN ch.{q.c(cc)} > pa.{q.c(pc)} THEN 1 ELSE 0 END), "
                                  f"SUM(CASE WHEN ch.{q.c(cc)} < pa.{q.c(pc)} THEN 1 ELSE 0 END), COUNT(*) {join} "
                                  f"WHERE ch.{q.c(cc)} IS NOT NULL AND pa.{q.c(pc)} IS NOT NULL")
            if _order(row) == "<=":  # child never above the parent
                add("lte_parent", child.name, cc, {"parent_table": parent.name, "parent_column": pc},
                    f"{child.name}.{cc} is at most {parent.name}.{pc}")


# --- helpers --------------------------------------------------------------------------


class _Quoter:
    def __init__(self, c: Connection, schema_name: str | None) -> None:
        self.prep = c.dialect.identifier_preparer
        self.schema_name = schema_name

    def t(self, name: str) -> str:
        table = self.prep.quote_identifier(name)
        return f"{self.prep.quote_identifier(self.schema_name)}.{table}" if self.schema_name else table

    def c(self, name: str) -> str:
        return self.prep.quote_identifier(name)


def _keys(t: TableSchema) -> set[str]:
    return {t.primary_key, *(fk.column for fk in t.foreign_keys)}


def _is_money(col: ColumnSchema) -> bool:
    return col.data_type in _NUMERIC and col.semantic_type == "currency_amount"


def _order(row) -> str | None:
    """From (a > b count, a < b count, rows): "<=" when a <= b everywhere (and < somewhere), ">=" for the reverse."""
    if not row or (row[2] or 0) < MIN_ROWS:
        return None
    gt, lt = row[0] or 0, row[1] or 0
    if gt == 0 and lt > 0:
        return "<="
    if lt == 0 and gt > 0:
        return ">="
    return None


def _row(c: Connection, budget: _Budget, sql: str, **params):
    if budget.left <= 0:
        budget.skipped += 1
        return None
    budget.left -= 1
    stmt = text(sql)
    if "vals" in params:
        stmt = stmt.bindparams(bindparam("vals", expanding=True))
    try:
        with c.begin_nested():  # one failed check must not abort the extract
            return c.execute(stmt, params).fetchone()
    except DBAPIError as exc:
        err = map_db_error(exc)
        if err.code == "db_auth_failed":
            raise err from None
        budget.skipped += 1
        return None
    except SQLAlchemyError as exc:
        logger.warning("Rule check failed: %s", type(exc).__name__)
        budget.skipped += 1
        return None


def _scalar(c: Connection, budget: _Budget, sql: str, **params):
    row = _row(c, budget, sql, **params)
    return None if row is None else row[0]
