import { useMemo, useState } from "react"
import { ArrowLeft } from "lucide-react"
import { errorMessage, schemaFromDb, schemaFromSqlite } from "@/api/client"
import type { DbTableInfo, ExtractMode, FromDbResponse } from "@/api/types"
import { Card } from "@/components/shared/Card"
import { ErrorCallout } from "@/components/shared/ErrorCallout"
import { MonoText } from "@/components/shared/MonoText"
import { SubmitButton } from "@/components/shared/SubmitButton"
import { Button } from "@/components/ui/button"
import { useStudio } from "@/state/useStudio"
import { DbConnectForm } from "./db/DbConnectForm"
import { DbExtractOptions } from "./db/DbExtractOptions"
import { DbImportResult } from "./db/DbImportResult"
import { DbStepIndicator } from "./db/DbStepIndicator"
import { DbTablePicker } from "./db/DbTablePicker"
import { SAMPLE_DEFAULT, sampleLimitError } from "./db/dbValidation"
import { defaultChoice, requiredParents } from "./db/tableSelection"
import { SourceLayout } from "./SourceLayout"

type Phase =
  | { kind: "connect" }
  | { kind: "tables"; tables: DbTableInfo[] }
  | { kind: "sqlite"; file: File }
  | { kind: "done"; result: FromDbResponse; source: "postgres" | "sqlite" }

export function DatabaseSource() {
  const { state, dispatch } = useStudio()
  const [phase, setPhase] = useState<Phase>({ kind: "connect" })
  const [chosen, setChosen] = useState<Set<string>>(new Set())
  const [mode, setMode] = useState<ExtractMode>("schema_and_sample")
  const [sampleLimit, setSampleLimit] = useState(String(SAMPLE_DEFAULT))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const autoAdded = useMemo(
    () => requiredParents(phase.kind === "tables" ? phase.tables : [], chosen),
    [phase, chosen],
  )
  const optionsValid = mode === "schema_only" || sampleLimitError(sampleLimit) === null
  const stepIndex = phase.kind === "connect" ? 0 : phase.kind === "done" ? 2 : 1

  const toggle = (name: string, checked: boolean) => {
    setChosen((prev) => {
      const next = new Set(prev)
      if (checked) next.add(name)
      else next.delete(name)
      return next
    })
  }

  const backToConnect = () => {
    setPhase({ kind: "connect" })
    setError(null)
  }

  const runImport = async () => {
    setLoading(true)
    setError(null)
    const limit = Number(sampleLimit) || SAMPLE_DEFAULT
    try {
      if (phase.kind === "sqlite") {
        const result = await schemaFromSqlite(phase.file, mode, limit)
        setPhase({ kind: "done", result, source: "sqlite" })
      } else if (phase.kind === "tables" && state.dbConnection) {
        const result = await schemaFromDb({
          connection: state.dbConnection,
          tables: [...chosen],
          mode,
          sample_limit: limit,
        })
        setPhase({ kind: "done", result, source: "postgres" })
      }
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const finish = (result: FromDbResponse, source: "postgres" | "sqlite") =>
    dispatch({
      type: "schemaLoaded",
      schema: result.schema,
      kind: source,
      notes: result.notes,
      autoAdded: result.auto_added,
      rowsSampled: result.rows_sampled,
    })

  return (
    <SourceLayout
      title="Connect a database"
      subtitle="DatDub reads the structure of your tables, and optionally a small sample, without ever writing to your database."
    >
      <Card>
        <DbStepIndicator current={stepIndex} />
        <div className="mt-6 border-t border-line pt-6">
          {phase.kind === "connect" && (
            <DbConnectForm
              onConnected={(connection, found) => {
                dispatch({ type: "setDbConnection", connection })
                setChosen(defaultChoice(found))
                setPhase({ kind: "tables", tables: found })
              }}
              onSqlite={(file) => setPhase({ kind: "sqlite", file })}
            />
          )}

          {(phase.kind === "tables" || phase.kind === "sqlite") && (
            <div className="space-y-6">
              {phase.kind === "tables" ? (
                <>
                  <div>
                    <h2 className="font-heading text-headline-sm font-medium text-ink">Choose tables</h2>
                    <p className="mt-1 text-body-md text-ink-muted">
                      Found {phase.tables.length} tables. Tables that your choices link to are added automatically.
                    </p>
                  </div>
                  <DbTablePicker
                    tables={phase.tables}
                    chosen={chosen}
                    autoAdded={autoAdded}
                    onToggle={toggle}
                    disabled={loading}
                  />
                </>
              ) : (
                <div>
                  <h2 className="font-heading text-headline-sm font-medium text-ink">Import settings</h2>
                  <p className="mt-1 text-body-md text-ink-muted">
                    All tables in <MonoText className="text-ink">{phase.file.name}</MonoText> will be read.
                  </p>
                </div>
              )}

              <DbExtractOptions
                mode={mode}
                onModeChange={setMode}
                sampleLimit={sampleLimit}
                onSampleLimitChange={setSampleLimit}
                disabled={loading}
              />

              {error && <ErrorCallout title="The import did not finish" message={error} />}

              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-5">
                <Button variant="ghost" onClick={backToConnect} disabled={loading}>
                  <ArrowLeft aria-hidden="true" />
                  Change connection
                </Button>
                <SubmitButton
                  loading={loading}
                  loadingLabel="Importing…"
                  disabled={!optionsValid || (phase.kind === "tables" && chosen.size === 0)}
                  onClick={runImport}
                >
                  Import {phase.kind === "tables" ? `${chosen.size + autoAdded.size} tables` : "tables"}
                </SubmitButton>
              </div>
            </div>
          )}

          {phase.kind === "done" && (
            <DbImportResult result={phase.result} onContinue={() => finish(phase.result, phase.source)} />
          )}
        </div>
      </Card>
    </SourceLayout>
  )
}
