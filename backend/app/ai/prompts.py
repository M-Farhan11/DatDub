"""Prompt builders for the three AI calls.

Each builder returns an `AIPrompt` whose `context` holds exactly the data
rendered into the prompt. Nothing here reads raw rows: callers pass
metadata and aggregates only (see the AI rules in CLAUDE.md).
"""

import json
from typing import Any, get_args

from app.ai.schemas import AIPrompt
from app.schemas.dataset import DataType, DatasetSchema, SemanticType

_SEMANTIC_TYPES = ", ".join(get_args(SemanticType))
_DATA_TYPES = ", ".join(get_args(DataType))

_RULE_CATALOGUE = """Rule catalogue (use only these kinds; fill only the fields for the kind):
- range: numeric column must lie in [min, max]
- allowed_values: column must be one of `values`
- date_order: `before` <= `column`. `before` is a column of the same table, or of the FK parent when `via_fk` names the FK column
- sum_of_children: column equals the sum over `child_table` rows of `expr` (one column name or "a * b")
- lte_parent: column must be <= `parent_column` of `parent_table` (through the FK)"""

_SCENARIO_CATALOGUE = """Scenario catalogue (use only these kinds):
- null_burst: several rows get NULL in a non-key column (set `column`); on a required column this is an intended "missing required value" test
- extreme_value: several rows get values far outside the normal range of a numeric column (set `column`)
- duplicate_record: several rows are duplicated with new primary keys (e.g. a duplicate payment)
- boundary_date: several rows get dates at boundaries: month end, leap day, far past/future (set `column` to a date column)
- rule_violation: several rows deliberately break an existing rule (set `rule_id` to one of the schema's rule ids)"""


def _dump(data: Any) -> str:
    return json.dumps(data, indent=1, default=str)


def schema_draft_prompt(user_prompt: str) -> AIPrompt:
    system = f"""You design relational schemas for a synthetic data generator.
Turn the user's description into 1-6 related tables.

Requirements:
- snake_case table and column names; every table has a string primary key column named "<singular>_id" (e.g. customer_id)
- child tables reference parents with a foreign key column of the same name as the parent's primary key
- data_type is one of: {_DATA_TYPES}
- semantic_type is one of: {_SEMANTIC_TYPES}
- mark person-identifying columns (names, emails, phones, addresses, IBANs) as pii=true
- use allowed_values for status/category columns; set min/max for numeric amounts and quantities
- max_children is a realistic upper bound of child rows per parent
- add rules only from the catalogue below and only when they are clearly implied
- put any assumptions you made in `notes` (short sentences)

{_RULE_CATALOGUE}"""
    return AIPrompt(
        task="schema_draft",
        system=system,
        user=f"Description:\n{user_prompt.strip()}",
        context={"prompt": user_prompt},
    )


def semantic_enrichment_prompt(tables: list[dict[str, Any]]) -> AIPrompt:
    """`tables`: [{"name", "columns": [{"name", "data_type", "stats"?, "categories"?}]}].

    The caller (ingest payload builder) is responsible for privacy filtering:
    aggregates only, category values only for low-cardinality non-PII columns.
    """
    system = f"""You label the columns of a dataset for a synthetic data generator.
You only see column names, data types and aggregate statistics, never rows.
For every column return: semantic_type (one of: {_SEMANTIC_TYPES}),
pii (true if it identifies a person: names, emails, phones, addresses, IBANs, national ids),
and confidence between 0 and 1. Return one entry per input column, with the exact table and column names."""
    return AIPrompt(
        task="semantic_enrichment",
        system=system,
        user=f"Columns:\n{_dump(tables)}",
        context={"tables": tables},
    )


def schema_summary(schema: DatasetSchema) -> dict[str, Any]:
    """Compact, row-free view of a schema (no profiles, no sample values)."""
    return {
        "tables": [
            {
                "name": t.name,
                "primary_key": t.primary_key,
                "columns": [
                    {"name": c.name, "data_type": c.data_type, "semantic_type": c.semantic_type, "nullable": c.nullable}
                    for c in t.columns
                ],
                "foreign_keys": [{"column": fk.column, "ref_table": fk.ref_table} for fk in t.foreign_keys],
            }
            for t in schema.tables
        ],
        "rules": [
            {"id": r.id, "kind": r.kind, "table": r.table, "column": r.column, "description": r.description}
            for r in schema.rules
        ],
    }


def scenario_plan_prompt(schema: DatasetSchema, instruction: str) -> AIPrompt:
    summary = schema_summary(schema)
    system = f"""You propose edge-case test scenarios for a synthetic dataset.
A deterministic engine injects each scenario after generation, so only choose from the catalogue.
Propose 3-6 varied, realistic scenarios that a QA or data engineer would want to test.
Reference only tables, columns and rule ids that exist in the schema.
title: short (max 8 words). description: what is injected. expected_behavior: what a correct
downstream application should do with these records. suggested_count: 3-25.

{_SCENARIO_CATALOGUE}"""
    return AIPrompt(
        task="scenario_plan",
        system=system,
        user=f"Instruction: {instruction.strip()}\n\nSchema:\n{_dump(summary)}",
        context={"schema": summary, "instruction": instruction},
    )

