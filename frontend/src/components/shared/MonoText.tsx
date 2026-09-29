import type { ComponentProps } from "react"
import { cn } from "@/lib/utils"

/** Table names, column names, IDs and numbers. */
export function MonoText({ className, ...props }: ComponentProps<"span">) {
  return <span className={cn("tabular font-mono text-code-md", className)} {...props} />
}
