"""Turn validated AI output into contract models.

Pydantic already guarantees the *shape* of AI output. This module checks the
*references* (tables, columns, FKs, rule ids) and drops or repairs anything
that does not fit the schema, returning a human-readable note for each fix.
"""

from app.ai.schemas import DraftRule, ScenarioPlan, SchemaDraft, SemanticEnrichment
from app.schemas.dataset import (
    ColumnSchema,
    DatasetSchema,
    DocumentHints,
    ForeignKey,
    InvoiceHints,
    Rule,
    SourceKind,
    TableSchema,
)
from app.schemas.report import ScenarioProposal

_NUMERIC = {"integer", "float", "decimal"}
_TEMPORAL = {"date", "datetime"}
MAX_CHILDREN_CAP = 50


# --- SchemaDraft -> DatasetSchema -------------------------------------------


def draft_to_schema(draft: SchemaDraft, source: SourceKind = "prompt") -> tuple[DatasetSchema, list[str]]:
    notes = list(draft.notes)
    tables: list[TableSchema] = []

    for dt in draft.tables:
        if any(t.name == dt.name for t in tables):
            notes.append(f"Dropped duplicate table '{dt.name}'.")
            continue
        columns: list[ColumnSchema] = []
        for dc in dt.columns:
            if any(c.name == dc.name for c in columns):
                continue
            columns.append(
                ColumnSchema(
                    name=dc.name,
                    data_type=dc.data_type,
                    semantic_type=dc.semantic_type,
                    nullable=dc.nullable,
                    unique=dc.unique,
                    pii=dc.pii,
                    allowed_values=dc.allowed_values or None,
                    min=dc.min,
                    max=dc.max,
                )
            )
        pk = next((c for c in columns if c.name == dt.primary_key), None)
        if pk is None:
            pk = ColumnSchema(name=dt.primary_key, data_type="string", semantic_type="id")
            columns.insert(0, pk)
            notes.append(f"Added missing primary key column {dt.name}.{dt.primary_key}.")
        pk.data_type, pk.semantic_type, pk.unique, pk.nullable, pk.pii = "string", "id", True, False, False
        tables.append(TableSchema(name=dt.name, primary_key=dt.primary_key, columns=columns))

    by_name = {t.name: t for t in tables}
    parents: dict[str, set[str]] = {t.name: set() for t in tables}

    linked: set[str] = set()
    for dt in draft.tables:
        table = by_name[dt.name]
        if dt.name in linked:  # duplicate draft table
            continue
        linked.add(dt.name)
        for dfk in dt.foreign_keys:
            parent = by_name.get(dfk.ref_table)
            if parent is None or parent.name == table.name:
                notes.append(f"Dropped foreign key {table.name}.{dfk.column} → unknown table '{dfk.ref_table}'.")
                continue
            if _reaches(parents, parent.name, table.name):
                notes.append(f"Dropped foreign key {table.name}.{dfk.column}: it would create a cycle.")
                continue
            if any(fk.column == dfk.column for fk in table.foreign_keys):
                continue
            col = next((c for c in table.columns if c.name == dfk.column), None)
            if col is None:
                col = ColumnSchema(name=dfk.column, data_type="string", semantic_type="id")
                table.columns.append(col)
            col.data_type, col.semantic_type, col.pii = "string", "id", False
            max_children = max(1, min(dfk.max_children, MAX_CHILDREN_CAP))
            table.foreign_keys.append(
                ForeignKey(
                    column=dfk.column,
                    ref_table=parent.name,
                    ref_column=parent.primary_key,  # the engine samples parent PKs
                    min_children=max(0, min(dfk.min_children, max_children)),
                    max_children=max_children,
                )
            )
            parents[table.name].add(parent.name)

    schema = DatasetSchema(name=_slug(draft.name) or "ai_schema", source=source, tables=tables)
    for dr in draft.rules:
        rule, problem = _convert_rule(dr, schema, f"r{len(schema.rules) + 1}")
        if rule is None:
            notes.append(f"Dropped rule on {dr.table}.{dr.column} ({dr.kind}): {problem}.")
        else:
            schema.rules.append(rule)
    schema.document_hints = invoice_hints(schema)
    return schema, notes


def _reaches(parents: dict[str, set[str]], start: str, target: str) -> bool:
    """True if `start` already depends (transitively) on `target`."""
    stack, seen = [start], set()
    while stack:
        node = stack.pop()
        if node == target:
            return True
        if node not in seen:
            seen.add(node)
            stack.extend(parents.get(node, ()))
    return False


def _slug(name: str) -> str:
    return "_".join("".join(ch if ch.isalnum() else " " for ch in name.lower()).split())


def _col(schema: DatasetSchema, table: str | None, column: str | None) -> ColumnSchema | None:
    t = schema.table(table or "")
    return next((c for c in t.columns if c.name == column), None) if t else None


def _fk(schema: DatasetSchema, child: str, parent: str | None) -> ForeignKey | None:
    t = schema.table(child)
    return next((fk for fk in t.foreign_keys if fk.ref_table == parent), None) if t else None


def _convert_rule(dr: DraftRule, schema: DatasetSchema, rule_id: str) -> tuple[Rule | None, str]:
    col = _col(schema, dr.table, dr.column)
    if col is None:
        return None, "unknown table or column"
    params: dict = {}

    if dr.kind == "range":
        if col.data_type not in _NUMERIC or (dr.min is None and dr.max is None):
            return None, "needs a numeric column and min/max"
        if dr.min is not None and dr.max is not None and dr.min > dr.max:
            return None, "min is greater than max"
        params = {"min": dr.min, "max": dr.max}
    elif dr.kind == "allowed_values":
        if not dr.values:
            return None, "no values given"
        params = {"values": dr.values}
        col.allowed_values = col.allowed_values or dr.values
    elif dr.kind == "date_order":
        if not dr.before or col.data_type not in _TEMPORAL:
            return None, "needs two date columns"
        if dr.via_fk:
            fk = next((f for f in schema.table(dr.table).foreign_keys if f.column == dr.via_fk), None)
            before_col = _col(schema, fk.ref_table, dr.before) if fk else None
        else:
            before_col = _col(schema, dr.table, dr.before)
        if before_col is None or before_col.data_type not in _TEMPORAL:
            return None, f"unknown date column '{dr.before}'"
        params = {"before": dr.before, "after": dr.column}
        if dr.via_fk:
            params["via_fk"] = dr.via_fk
    elif dr.kind == "sum_of_children":
        if not dr.child_table or _fk(schema, dr.child_table, dr.table) is None:
            return None, "child table is not linked by a foreign key"
        parts = [p.strip() for p in (dr.expr or "").split("*")]
        if not (1 <= len(parts) <= 2) or any(_col(schema, dr.child_table, p) is None for p in parts):
            return None, f"expression '{dr.expr}' uses unknown columns"
        params = {"child_table": dr.child_table, "expr": " * ".join(parts)}
    elif dr.kind == "lte_parent":
        if _fk(schema, dr.table, dr.parent_table) is None or _col(schema, dr.parent_table, dr.parent_column) is None:
            return None, "parent table/column is not linked by a foreign key"
        params = {"parent_table": dr.parent_table, "parent_column": dr.parent_column}

    return Rule(id=rule_id, kind=dr.kind, table=dr.table, column=dr.column, params=params, description=dr.description), ""


def invoice_hints(schema: DatasetSchema) -> DocumentHints | None:
    """Detect an invoice header → items → party shape so the invoice PDF works."""
    for header in schema.tables:
        if "invoice" not in header.name or "item" in header.name or "line" in header.name:
            continue
        items = next(
            (t for t in schema.tables if ("item" in t.name or "line" in t.name) and _fk(schema, t.name, header.name)),
            None,
        )
        party = header.foreign_keys[0].ref_table if header.foreign_keys else None
        if items and party:
            return DocumentHints(invoice=InvoiceHints(header_table=header.name, items_table=items.name, party_table=party))
    return None


# --- SemanticEnrichment -> schema --------------------------------------------


_NUMERIC_SEMANTICS = {"currency_amount", "quantity", "percentage", "generic_number"}


def apply_enrichment(schema: DatasetSchema, enrichment: SemanticEnrichment, keep_above: float | None = None) -> int:
    """Apply AI column semantics in place. Returns the number applied.

    PK/FK columns stay `id`. A semantic type that does not fit the column's
    data type is ignored. With `keep_above`, columns whose current
    confidence is at least that value (e.g. confirmed by a value regex)
    keep their semantic type. PII is only ever added, never removed, and a
    column that becomes PII loses any sampled category values.
    """
    applied = 0
    for item in enrichment.columns:
        table = schema.table(item.table)
        col = _col(schema, item.table, item.column)
        if table is None or col is None:
            continue
        if col.name == table.primary_key or any(fk.column == col.name for fk in table.foreign_keys):
            continue
        if keep_above is not None and col.confidence >= keep_above:
            continue
        if item.semantic_type in _NUMERIC_SEMANTICS and col.data_type not in _NUMERIC:
            continue
        if col.data_type in _NUMERIC and item.semantic_type not in _NUMERIC_SEMANTICS | {"category", "status"}:
            continue
        if item.semantic_type in _TEMPORAL and col.data_type not in _TEMPORAL:
            continue
        col.semantic_type, col.confidence = item.semantic_type, item.confidence
        col.pii = col.pii or item.pii
        if col.pii:
            col.allowed_values = None
            if col.profile is not None:
                col.profile.top_values = None
        applied += 1
    return applied


# --- ScenarioPlan -> proposals -----------------------------------------------


def validate_proposals(plan: ScenarioPlan, schema: DatasetSchema) -> list[ScenarioProposal]:
    """Keep only proposals whose references exist and fit their kind."""
    rule_ids = {r.id: r for r in schema.rules}
    proposals: list[ScenarioProposal] = []
    for p in plan.proposals:
        table = schema.table(p.table)
        if table is None:
            continue
        col = _col(schema, p.table, p.column) if p.column else None
        if p.kind == "null_burst" and not (col and col.name != table.primary_key):
            continue
        if p.kind == "extreme_value" and not (col and col.data_type in _NUMERIC):
            continue
        if p.kind == "boundary_date" and not (col and col.data_type in _TEMPORAL):
            continue
        if p.kind == "rule_violation":
            rule = rule_ids.get(p.rule_id or "")
            if rule is None or rule.table != p.table:
                continue
            col = _col(schema, rule.table, rule.column)
        proposals.append(
            ScenarioProposal(
                id=f"s{len(proposals) + 1}",
                kind=p.kind,
                table=p.table,
                column=col.name if col else None,
                rule_id=p.rule_id if p.kind == "rule_violation" else None,
                title=p.title,
                suggested_count=p.suggested_count,
                description=p.description,
                expected_behavior=p.expected_behavior,
            )
        )
    return proposals
