# Design

Status: **LOCKED for MVP** (2026-09-29). Owner: Haider.

## Principles
- One workspace, guided in 5 steps, with no code required
- The AI contribution is **visible** (confidence badges, "AI proposed" labels)
- Validation is shown as evidence (PASS/FAIL cards with numbers)
- Demo-friendly: large readable graph and a "Load demo" shortcut on each input

## Frontend Technology
React + TypeScript + Vite + Tailwind + shadcn/ui ·
`@xyflow/react` (schema graph) · `@tanstack/react-table` (previews) ·
Recharts (stretch: similarity charts). No Next.js, no router needed beyond simple step state.

## Layout
Taken from the theme PDF: dark navy left sidebar (Workspace: Tabular /
Relational / Documents), a main canvas in the centre, and a configuration
panel on the right where relevant. A stepper sits across the top.

## Pages / Steps
1. **Source**: tabs Prompt · CSV · Database · Templates
2. **Schema**: React Flow graph (tables, PK/FK, `1:N` edges) + field inspector panel + rules list
3. **Configure**: rows, seed, null %, outlier %, locale + **Scenario Studio** (instruction → proposals checklist with counts)
4. **Results**: tabs Data (per-table table) · Quality (report cards) · Ground Truth · Documents (invoice PDF viewer)
5. **Export**: ZIP download + per-table CSV/JSON

## User Flow
Source → (AI inference, loading state) → Schema review/edit → Configure + pick
scenarios → Generate (progress) → Results → Export

## Components
`AppShell`, `Stepper`, `SourceTabs`, `PromptInput`, `CsvDropzone`, `DbConnectForm`,
`TemplateCards`, `SchemaGraph`, `TableNode`, `FieldInspector`, `RulesList`,
`ConfigPanel`, `ScenarioStudio`, `DataPreviewTable`, `QualityReport`,
`GroundTruthList`, `InvoiceViewer`, `ExportPanel`

## Color Palette (from the theme PDF)
- Navy `#16213A` (sidebar, headings)
- Teal `#157A6E` (primary actions, active states)
- Light teal `#E3F1EF` (chips, badges)
- Warm off-white `#F3F0EA` / `#FAFAF8` (backgrounds)
- Status: PASS green, FAIL red, "expected (injected)" amber
- Font: a geometric sans for headings, IBM Plex Sans (or similar) for body

## Stitch Usage
Optional. Stitch may be used for a first pass at the Schema and Results
screens. Claude implements the final React UI.
