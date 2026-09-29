import { useState } from "react"
import { FileText, X } from "lucide-react"
import { errorMessage, schemaFromCsv } from "@/api/client"
import { Card } from "@/components/shared/Card"
import { ErrorCallout } from "@/components/shared/ErrorCallout"
import { MonoText } from "@/components/shared/MonoText"
import { SubmitButton } from "@/components/shared/SubmitButton"
import { formatBytes } from "@/lib/format"
import { useStudio } from "@/state/useStudio"
import { CsvDropzone } from "./CsvDropzone"
import { SourceLayout } from "./SourceLayout"

export function CsvSource() {
  const { dispatch } = useStudio()
  const [files, setFiles] = useState<File[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const addFiles = (incoming: File[]) => {
    setNotice(null)
    setFiles((prev) => {
      const names = new Set(prev.map((f) => f.name))
      return [...prev, ...incoming.filter((f) => !names.has(f.name))]
    })
  }

  const submit = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await schemaFromCsv(files)
      dispatch({ type: "schemaLoaded", schema: res.schema, kind: "csv", notes: res.notes })
    } catch (err) {
      setError(errorMessage(err))
      setLoading(false)
    }
  }

  return (
    <SourceLayout
      title="Upload CSV files"
      subtitle="DatDub reads column types, keys and value patterns, then links the files into one schema."
    >
      <Card>
        <CsvDropzone
          onFiles={addFiles}
          disabled={loading}
          onRejected={(names) => setNotice(`Skipped ${names.join(", ")}: only .csv files are accepted.`)}
        />
        {notice && <p className="mt-3 text-body-sm text-fail">{notice}</p>}

        {files.length > 0 && (
          <ul aria-label="Selected files" className="mt-5 divide-y divide-line rounded-xl border border-line">
            {files.map((file) => (
              <li key={file.name} className="flex items-center gap-3 px-4 py-2.5">
                <FileText className="size-4 shrink-0 text-hint" aria-hidden="true" />
                <MonoText className="min-w-0 flex-1 truncate text-ink">{file.name}</MonoText>
                <span className="tabular text-body-sm text-ink-muted">{formatBytes(file.size)}</span>
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => setFiles((prev) => prev.filter((f) => f.name !== file.name))}
                  aria-label={`Remove ${file.name}`}
                  className="flex size-8 items-center justify-center rounded-full text-ink-muted transition-colors hover:bg-surface-low hover:text-fail disabled:opacity-50"
                >
                  <X className="size-4" aria-hidden="true" />
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-line pt-5">
          <p className="text-body-sm text-ink-muted">
            Files are read on the server to learn types and statistics. The AI sees column names and statistics only.
          </p>
          <SubmitButton
            loading={loading}
            loadingLabel="Analyzing files…"
            disabled={files.length === 0}
            title={files.length === 0 ? "Add at least one CSV file" : undefined}
            onClick={submit}
          >
            Analyze {files.length > 1 ? `${files.length} files` : "files"}
          </SubmitButton>
        </div>
      </Card>

      {error && <ErrorCallout className="mt-4" title="The files could not be analyzed" message={error} />}
    </SourceLayout>
  )
}
