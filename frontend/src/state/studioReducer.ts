import type {
  ColumnSchema,
  DatasetSchema,
  DbConnection,
  GenerateResponse,
  ScenarioProposal,
  ScenarioSelection,
  SourceKind,
} from "@/api/types"
import { STEPS, type Step } from "@/components/studio/steps"

export type SourceScreen = "picker" | "prompt" | "csv" | "database" | "template"

export type ResultsTab = "checks" | "data" | "edge-cases" | "invoices"

export interface ColumnRef {
  table: string
  column: string
}

export interface GenerationConfig {
  /** counts for root tables only */
  rows: Record<string, number>
  seed: number
  null_rate: number
  outlier_rate: number
  locale: string
}

export interface StudioState {
  step: Step
  /** index of the furthest step reached; steps up to it are clickable */
  reached: number
  sourceScreen: SourceScreen
  sourceKind: SourceKind | null
  schema: DatasetSchema | null
  notes: string[]
  autoAdded: string[]
  rowsSampled: number | null
  selectedColumn: ColumnRef | null
  config: GenerationConfig
  instruction: string
  proposals: ScenarioProposal[]
  /** proposal id -> count; presence means selected */
  selectedScenarios: Record<string, number>
  result: GenerateResponse | null
  /** Open tab on the Results step, and the table shown in its Data tab. */
  resultsTab: ResultsTab
  dataTable: string | null
  /** Settings and scenarios the current result was generated with. */
  generatedWith: { config: GenerationConfig; scenarios: ScenarioSelection[] } | null
  /** Memory only: never persisted, never logged. */
  dbConnection: DbConnection | null
}

export type StudioAction =
  | { type: "goTo"; step: Step }
  | { type: "advance"; step: Step }
  | { type: "openSource"; screen: SourceScreen }
  | {
      type: "schemaLoaded"
      schema: DatasetSchema
      kind: SourceKind
      notes?: string[]
      autoAdded?: string[]
      rowsSampled?: number | null
    }
  | { type: "selectColumn"; ref: ColumnRef | null }
  | { type: "updateColumn"; ref: ColumnRef; patch: Partial<ColumnSchema> }
  | { type: "setConfig"; patch: Partial<GenerationConfig> }
  | { type: "setRows"; table: string; count: number }
  | { type: "setInstruction"; instruction: string }
  | { type: "setProposals"; proposals: ScenarioProposal[] }
  | { type: "toggleScenario"; id: string; on: boolean }
  | { type: "setScenarioCount"; id: string; count: number }
  | { type: "generated"; result: GenerateResponse; config: GenerationConfig; scenarios: ScenarioSelection[] }
  | { type: "clearResult" }
  | { type: "openResults"; tab: ResultsTab; table?: string | null }
  | { type: "setDbConnection"; connection: DbConnection | null }
  | { type: "reset" }

export const DEFAULT_INSTRUCTION = "Add realistic edge cases for testing"

export const DEFAULT_CONFIG: GenerationConfig = {
  rows: {},
  seed: 42,
  null_rate: 0.02,
  outlier_rate: 0.01,
  locale: "en_US",
}

export const initialStudioState: StudioState = {
  step: "Source",
  reached: 0,
  sourceScreen: "picker",
  sourceKind: null,
  schema: null,
  notes: [],
  autoAdded: [],
  rowsSampled: null,
  selectedColumn: null,
  config: DEFAULT_CONFIG,
  instruction: DEFAULT_INSTRUCTION,
  proposals: [],
  selectedScenarios: {},
  result: null,
  resultsTab: "checks",
  dataTable: null,
  generatedWith: null,
  dbConnection: null,
}

export const stepIndex = (step: Step) => STEPS.indexOf(step)

/** Root tables have no foreign keys; their row counts drive every child table. */
export function rootTables(schema: DatasetSchema) {
  return schema.tables.filter((t) => t.foreign_keys.length === 0)
}

export function studioReducer(state: StudioState, action: StudioAction): StudioState {
  switch (action.type) {
    case "goTo": {
      const idx = stepIndex(action.step)
      if (idx > state.reached) return state
      return { ...state, step: action.step }
    }
    case "advance":
      return { ...state, step: action.step, reached: Math.max(state.reached, stepIndex(action.step)) }
    case "openSource":
      return { ...state, step: "Source", sourceScreen: action.screen }
    case "schemaLoaded": {
      // A new schema starts a new dataset: later steps are cleared.
      const rows = Object.fromEntries(
        rootTables(action.schema).map((t) => [t.name, t.row_count_hint ?? 5000]),
      )
      return {
        ...initialStudioState,
        dbConnection: state.dbConnection,
        step: "Schema",
        reached: stepIndex("Schema"),
        sourceScreen: "picker",
        sourceKind: action.kind,
        schema: action.schema,
        notes: action.notes ?? [],
        autoAdded: action.autoAdded ?? [],
        rowsSampled: action.rowsSampled ?? null,
        config: { ...DEFAULT_CONFIG, rows },
      }
    }
    case "selectColumn":
      return { ...state, selectedColumn: action.ref }
    case "updateColumn": {
      if (!state.schema) return state
      const { table, column } = action.ref
      return {
        ...state,
        schema: {
          ...state.schema,
          tables: state.schema.tables.map((t) =>
            t.name !== table
              ? t
              : { ...t, columns: t.columns.map((c) => (c.name === column ? { ...c, ...action.patch } : c)) },
          ),
        },
      }
    }
    case "setConfig":
      return { ...state, config: { ...state.config, ...action.patch } }
    case "setRows":
      return { ...state, config: { ...state.config, rows: { ...state.config.rows, [action.table]: action.count } } }
    case "setInstruction":
      return { ...state, instruction: action.instruction }
    case "setProposals": {
      const selectedScenarios = Object.fromEntries(
        Object.entries(state.selectedScenarios).filter(([id]) => action.proposals.some((p) => p.id === id)),
      )
      return { ...state, proposals: action.proposals, selectedScenarios }
    }
    case "toggleScenario": {
      const selectedScenarios = { ...state.selectedScenarios }
      if (action.on) {
        const proposal = state.proposals.find((p) => p.id === action.id)
        selectedScenarios[action.id] = proposal?.suggested_count ?? 1
      } else {
        delete selectedScenarios[action.id]
      }
      return { ...state, selectedScenarios }
    }
    case "setScenarioCount":
      return { ...state, selectedScenarios: { ...state.selectedScenarios, [action.id]: action.count } }
    case "generated":
      return {
        ...state,
        result: action.result,
        generatedWith: { config: action.config, scenarios: action.scenarios },
        resultsTab: "checks",
        dataTable: null,
        step: "Results",
        reached: stepIndex("Results"),
      }
    case "clearResult":
      return { ...state, result: null, generatedWith: null, step: "Configure", reached: stepIndex("Configure") }
    case "openResults":
      if (!state.result) return state
      return {
        ...state,
        step: "Results",
        reached: Math.max(state.reached, stepIndex("Results")),
        resultsTab: action.tab,
        dataTable: action.table === undefined ? state.dataTable : action.table,
      }
    case "setDbConnection":
      return { ...state, dbConnection: action.connection }
    case "reset":
      return initialStudioState
  }
}
