import { cn } from "@/lib/utils"

export function NodeTag({ children, tone }: { children: string; tone: "pk" | "fk" | "pii" }) {
  return (
    <span
      className={cn(
        "rounded-full px-1.5 font-heading text-[10px] leading-4 font-semibold tracking-wide",
        tone === "pk" && "bg-surface text-ink-muted",
        tone === "fk" && "bg-surface-high text-primary",
        tone === "pii" && "bg-primary-tint text-primary-deep",
      )}
    >
      {children}
    </span>
  )
}
