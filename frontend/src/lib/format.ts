const intFormat = new Intl.NumberFormat("en-US")

export const formatInt = (n: number) => intFormat.format(n)

export const formatPercent = (ratio: number, digits = 0) => `${(ratio * 100).toFixed(digits)}%`

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export const humanize = (s: string) => s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase())
