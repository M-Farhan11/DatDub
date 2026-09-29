import { CircleAlert, CircleCheck, CircleX } from "lucide-react"
import { cn } from "@/lib/utils"

export type Status = "pass" | "fail" | "expected"

const STYLES: Record<Status, { label: string; className: string; Icon: typeof CircleCheck }> = {
  pass: { label: "Pass", className: "bg-pass/10 text-pass", Icon: CircleCheck },
  fail: { label: "Fail", className: "bg-fail/10 text-fail", Icon: CircleX },
  expected: { label: "Expected", className: "bg-expected/10 text-expected", Icon: CircleAlert },
}

interface StatusTagProps {
  status: Status
  /** Override the default label ("Pass", "Fail", "Expected"). */
  label?: string
  className?: string
}

/** Status is always icon + word, never colour alone. */
export function StatusTag({ status, label, className }: StatusTagProps) {
  const { label: fallback, className: tone, Icon } = STYLES[status]
  return (
    <span
      className={cn(
        "inline-flex h-6 shrink-0 items-center gap-1 rounded-full px-2.5 font-heading text-label-md font-medium whitespace-nowrap",
        tone,
        className,
      )}
    >
      <Icon className="size-3.5" aria-hidden="true" />
      {label ?? fallback}
    </span>
  )
}
