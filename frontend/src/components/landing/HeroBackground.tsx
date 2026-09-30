import { useMemo } from "react"

const COLS = 18
const ROWS = 9
// Palette weights: mostly tints, some brand blue and cyan, a rare coral cell.
const FILLS = [
  "bg-primary-tint",
  "bg-primary-tint",
  "bg-surface-highest",
  "bg-surface-highest",
  "bg-cyan/50",
  "bg-primary/25",
  "bg-primary/45",
  "bg-coral/40",
]

/** Tiny seeded PRNG so the cell pattern is identical on every render. */
function mulberry32(seed: number) {
  return () => {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/**
 * Hero backdrop: a grid of table cells in the brand palette that slowly
 * "fill in", like rows being generated, over two soft colour washes.
 * CSS keyframes only (cheap), frozen under prefers-reduced-motion.
 */
export function HeroBackground() {
  const cells = useMemo(() => {
    const rand = mulberry32(42)
    return Array.from({ length: COLS * ROWS }, (_, i) => {
      const r = rand()
      const fill = FILLS[Math.floor(rand() * FILLS.length)]
      return {
        key: i,
        // About a third of the cells stay empty outlines.
        fill: r < 0.34 ? null : fill,
        delay: `${(rand() * 9).toFixed(2)}s`,
        duration: `${(6 + rand() * 6).toFixed(2)}s`,
        wide: rand() < 0.18,
      }
    })
  }, [])

  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div className="absolute -top-40 left-1/2 size-[640px] -translate-x-[70%] animate-drift-a rounded-full bg-primary/20 blur-[120px]" />
      <div className="absolute top-10 left-1/2 size-[520px] -translate-x-[10%] animate-drift-b rounded-full bg-cyan/40 blur-[120px]" />
      <div className="absolute bottom-0 left-1/2 size-[260px] translate-x-[60%] animate-drift-a rounded-full bg-coral/15 blur-[100px]" />

      <div
        className="absolute inset-x-[-4%] inset-y-[6%] grid gap-2 [mask-image:radial-gradient(ellipse_62%_58%_at_50%_48%,transparent_18%,black_58%,transparent_92%)]"
        style={{ gridTemplateColumns: `repeat(${COLS}, minmax(0, 1fr))`, gridAutoRows: "clamp(28px, 4.2vw, 52px)" }}
      >
        {cells.map((cell) => (
          <span
            key={cell.key}
            className={
              cell.fill
                ? `hero-cell rounded-md ${cell.fill} ${cell.wide ? "col-span-2" : ""}`
                : "rounded-md border border-chrome/70"
            }
            style={cell.fill ? { animationDelay: cell.delay, animationDuration: cell.duration } : undefined}
          />
        ))}
      </div>
      <div className="grain absolute inset-0 opacity-[0.05] mix-blend-multiply" />
    </div>
  )
}
