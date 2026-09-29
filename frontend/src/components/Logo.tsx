import logoUrl from "@/assets/logo.svg"
import { cn } from "@/lib/utils"

interface LogoProps {
  /** Size of the mark in pixels. */
  size?: number
  withText?: boolean
  textClassName?: string
  className?: string
}

/** DatDub mark + wordmark ("Dat" in ink, "Dub" in the theme blue). */
export function Logo({ size = 32, withText = true, textClassName, className }: LogoProps) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <img src={logoUrl} alt="" width={size} height={size} className="shrink-0" />
      {withText && (
        <span className={cn("font-sans text-headline-md font-bold tracking-tight", textClassName)}>
          <span className="text-ink">Dat</span>
          <span className="text-primary">Dub</span>
        </span>
      )}
    </span>
  )
}
