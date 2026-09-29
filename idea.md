# Idea

Status: **LOCKED** (2026-09-29)

## Theme
Synthetic Data Platform (HackDataV2). Realistic, privacy-safe tabular,
relational and document data, generated on demand.

## Problem
- Teams can't freely share production data (privacy and compliance).
- Real datasets are small, skewed, and missing the edge cases engineers need.
- Getting a sanctioned data extract takes weeks.
- Existing "fake data" tools produce random rows that break relationships and
  business rules, so the data is useless for testing real applications.

## Target Users
Developers and QA engineers who need realistic test and demo databases.
Data teams who need shareable stand-ins for production data.

## Proposed Solution
**A constraint-aware synthetic data studio.** Give it a description, CSV
files, a database connection, or a template. It will:

1. **Understand** the structure and business meaning of the data (AI + deterministic inference).
2. **Show** it as a relationship graph that the user can review and correct.
3. **Plan** generation: distributions, business rules, and AI-proposed edge-case scenarios.
4. **Generate** an entire coherent, fake-but-valid relational world (deterministic engine, seeded).
5. **Prove** it is valid: PK uniqueness, FK integrity, business-rule checks, and statistical similarity.
6. **Export** data + documents (invoice PDFs) + **ground truth** of every injected test case.

Positioning line: *not a fake-data generator, a test-environment generator.*

## Why AI?
- Schema semantics: "this column is an email, this is PII, this is a currency amount".
- Prompt → full relational schema with rules.
- Scenario proposals: realistic edge cases for this specific domain.

AI produces **structured plans only**. Deterministic code generates every
row, which makes the output reproducible and verifiable. Raw rows are never
sent to the LLM.

## Core User Flow
Source → Schema graph → Configure + Scenarios → Results (preview, quality, ground truth, documents) → Export

## Must Have
- Inputs: prompt, CSV upload, Postgres connection (Supabase demo DB), SQLite upload, 2 templates
- Schema inference: types, PK/FK, semantic types, PII flags, AI confidence
- Interactive schema graph + field inspector
- Generation: row count, seed, null %, outlier %, locale, FK-consistent, rules enforced
- Scenario Studio: AI proposes → user selects → deterministic injection → ground truth
- Validation report: PK, FK, rules, similarity (when a sample exists)
- Invoice PDF from generated data
- Export: CSV, JSON, ZIP (with schema, report, ground truth, PDFs)

## Should Have (only if time allows)
See the Enhancements backlog in `TASKS.md`.

## Cut
Auth/RBAC, platform database, SDV/model training, differential-privacy claims,
extra DB dialects, full accounting statements, AI-generated rows.

## Success Criteria
- The canonical demo runs end-to-end on the deployed URLs in under 3 minutes.
- 5,000-row finance dataset: FK integrity 100%, all rules PASS apart from
  injected scenarios (reported as expected).
- The same seed gives an identical dataset.
- The demo works offline using the template + MockProvider.

## Canonical Demo Scenario
1. **Connect** the Supabase demo DB (schema + sample).
2. **Understand**: the relationship graph appears; click `email` to see PII, 96% confidence.
3. **Define**: 5,000 customers, seed 42. "Add realistic edge cases for testing."
4. **AI plan**: the proposed scenarios appear; tick 3.
5. **Generate**.
6. **Validate**: integrity 100%, rules pass, 3 scenarios injected as expected, similarity %.
7. **Inspect**: preview tables.
8. **Document**: open a synthetic invoice PDF whose total reconciles.
9. **Ground truth**: exactly which records were made tricky, and why.
10. **Export**: ZIP.
