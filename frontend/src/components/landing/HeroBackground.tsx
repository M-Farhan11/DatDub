/**
 * Two soft blurred shapes drifting slowly behind the hero, plus a faint grain.
 * CSS keyframes only (see `drift-a` / `drift-b` in globals.css); motion stops
 * under prefers-reduced-motion.
 */
export function HeroBackground() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div className="absolute top-1/4 left-1/2 size-[420px] -translate-x-3/4 -translate-y-1/2 animate-drift-a rounded-full bg-primary/10 blur-[90px]" />
      <div className="absolute top-1/3 left-1/2 size-[380px] -translate-x-1/4 -translate-y-1/3 animate-drift-b rounded-full bg-cyan/30 blur-[80px]" />
      <div className="grain absolute inset-0 opacity-[0.07] mix-blend-multiply" />
    </div>
  )
}
