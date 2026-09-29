import { useRef, useState, type DragEvent } from "react"
import { FileUp } from "lucide-react"
import { cn } from "@/lib/utils"

interface CsvDropzoneProps {
  onFiles: (files: File[]) => void
  disabled?: boolean
  /** Reports files that were skipped because they are not .csv. */
  onRejected: (names: string[]) => void
}

const isCsv = (file: File) => file.name.toLowerCase().endsWith(".csv")

export function CsvDropzone({ onFiles, disabled, onRejected }: CsvDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  const accept = (list: FileList | null) => {
    if (!list) return
    const files = Array.from(list)
    const rejected = files.filter((f) => !isCsv(f)).map((f) => f.name)
    if (rejected.length) onRejected(rejected)
    const csv = files.filter(isCsv)
    if (csv.length) onFiles(csv)
  }

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragging(false)
    if (!disabled) accept(e.dataTransfer.files)
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault()
        if (!disabled) setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-12 text-center transition-colors",
        dragging ? "border-primary bg-primary-tint/40" : "border-line bg-surface-low",
        disabled && "opacity-60",
      )}
    >
      <span className="flex size-12 items-center justify-center rounded-lg bg-card text-primary-deep shadow-sm">
        <FileUp className="size-6" aria-hidden="true" />
      </span>
      <div>
        <p className="font-heading text-headline-sm font-medium text-ink">Drop CSV files here</p>
        <p className="mt-1 text-body-md text-ink-muted">One file per table. The first row must hold the column names.</p>
      </div>
      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        className="h-9 rounded-full border border-line bg-card px-4 font-heading text-label-lg font-medium text-primary-deep shadow-sm transition-colors hover:border-primary disabled:opacity-50"
      >
        Browse files
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".csv,text/csv"
        multiple
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        onChange={(e) => {
          accept(e.target.files)
          e.target.value = ""
        }}
      />
    </div>
  )
}
