import { cn } from "@/lib/utils"
import { Stepper } from "./Stepper"
import type { Step } from "./steps"

interface TopBarProps {
  title: string
  step: Step
  reached: number
  onSelectStep: (step: Step) => void
  sidebarExpanded: boolean
}

export function TopBar({ title, step, reached, onSelectStep, sidebarExpanded }: TopBarProps) {
  return (
    <header
      className={cn(
        "fixed top-0 right-0 left-16 z-40 flex h-16 items-center justify-between gap-4 border-b border-line bg-card px-4 transition-[left] duration-200 ease-out md:px-gutter-lg",
        sidebarExpanded && "md:left-52",
      )}
    >
      <span className="hidden min-w-0 truncate font-heading text-headline-sm font-semibold tracking-tight text-ink sm:inline sm:max-w-48">
        {title}
      </span>
      <Stepper current={step} reached={reached} onSelect={onSelectStep} />
      <span className="hidden w-24 sm:block" aria-hidden="true" />
    </header>
  )
}
