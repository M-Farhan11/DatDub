import type { Row } from "@/api/types"

/** RFC 4180 CSV: values with commas, quotes or line breaks are quoted; null is empty. */
export function toCsv(rows: Row[], columns: string[]): string {
  const cell = (v: Row[string] | undefined) => {
    if (v === null || v === undefined) return ""
    const s = String(v)
    return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  const lines = [columns.map((c) => cell(c)).join(",")]
  for (const row of rows) lines.push(columns.map((c) => cell(row[c])).join(","))
  return `${lines.join("\r\n")}\r\n`
}

/** Saves a Blob or text as a file through a temporary link. */
export function downloadBlob(filename: string, content: Blob | string, mime = "text/plain"): void {
  const blob = typeof content === "string" ? new Blob([content], { type: mime }) : content
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
