/**
 * Hero backdrop: a faint dot grid (fading out at the edges), two soft blurred
 * shapes drifting slowly, and a very light grain. CSS only; motion stops under
 * prefers-reduced-motion.
 */
export function HeroBackground() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div className="dot-grid absolute inset-0 [mask-image:radial-gradient(ellipse_70%_60%_at_50%_40%,black_30%,transparent_80%)]" />
      <div className="absolute top-1/4 left-1/2 size-[420px] -translate-x-3/4 -translate-y-1/2 animate-drift-a rounded-full bg-primary/10 blur-[90px]" />
      <div className="absolute top-1/3 left-1/2 size-[380px] -translate-x-1/4 -translate-y-1/3 animate-drift-b rounded-full bg-primary-tint/70 blur-[80px]" />
      <div className="grain absolute inset-0 opacity-[0.06] mix-blend-multiply" />
    </div>
  )
}
