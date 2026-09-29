import type { ReactNode } from "react"
import { CircleAlert } from "lucide-react"
import { cn } from "@/lib/utils"

interface ErrorCalloutProps {
  message: string
  title?: string
  action?: ReactNode
  className?: string
}

/** Shows an API error message as-is (backend messages never echo credentials). */
export function ErrorCallout({ message, title, action, className }: ErrorCalloutProps) {
  return (
    <div
      role="alert"
      className={cn("flex items-start gap-3 rounded-xl border border-fail/25 bg-fail/5 px-4 py-3 text-fail", className)}
    >
      <CircleAlert className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
      <div className="min-w-0 flex-1 text-body-md">
        {title && <p className="font-heading font-medium">{title}</p>}
        <p className={cn(title && "text-ink-muted")}>{message}</p>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}
