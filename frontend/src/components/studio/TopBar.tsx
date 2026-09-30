import { Logo } from "@/components/Logo"
import { cn } from "@/lib/utils"
import { Stepper } from "./Stepper"
import type { Step } from "./steps"

interface TopBarProps {
  title: string
  step: Step
  reached: number
  onSelectStep: (step: Step) => void
  sidebar: "none" | "collapsed" | "expanded"
  onHome: () => void
}

export function TopBar({ title, step, reached, onSelectStep, sidebar, onHome }: TopBarProps) {
  return (
    <header
      className={cn(
        "fixed top-0 right-0 z-40 flex h-16 items-center justify-between gap-4 border-b border-line bg-card px-4 transition-[left] duration-200 ease-out md:px-gutter-lg",
        sidebar === "none" ? "left-0" : "left-16",
        sidebar === "expanded" && "md:left-52",
      )}
    >
      {/* Without the sidebar the logo lives here, so there is always a way home. */}
      {sidebar === "none" ? (
        <button type="button" onClick={onHome} aria-label="DatDub home" className="shrink-0 rounded-lg">
          <Logo size={30} withText={false} className="sm:hidden" />
          <Logo size={30} textClassName="text-headline-sm" className="hidden sm:inline-flex" />
        </button>
      ) : (
        <span className="hidden min-w-0 truncate font-heading text-headline-sm font-semibold tracking-tight text-ink sm:inline sm:max-w-48">
          {title}
        </span>
      )}
      <Stepper current={step} reached={reached} onSelect={onSelectStep} />
      <span className="hidden w-24 sm:block" aria-hidden="true" />
    </header>
  )
}
