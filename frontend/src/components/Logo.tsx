import logoUrl from "@/assets/logo.svg"
import { cn } from "@/lib/utils"

interface LogoProps {
  /** Size of the mark in pixels. */
  size?: number
  withText?: boolean
  textClassName?: string
  className?: string
}

export function Logo({ size = 32, withText = true, textClassName, className }: LogoProps) {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <img src={logoUrl} alt="" width={size} height={size} className="shrink-0" />
      {withText && (
        <span className={cn("font-heading text-headline-md font-medium tracking-tight text-ink", textClassName)}>
          DatDub
        </span>
      )}
    </span>
  )
}
