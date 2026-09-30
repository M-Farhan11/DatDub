import { motion, useReducedMotion } from "motion/react"
import { ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { HeroBackground } from "./HeroBackground"

interface HeroProps {
  onLaunch: () => void
}

const LETTERS = [..."Dat"].map((c) => ({ c, tone: "text-ink" })).concat([..."Dub"].map((c) => ({ c, tone: "text-primary" })))

export function Hero({ onLaunch }: HeroProps) {
  const reduce = useReducedMotion()

  return (
    <section
      aria-labelledby="hero-title"
      className="relative isolate flex min-h-[calc(100dvh-4rem)] w-full items-center overflow-hidden py-20"
    >
      <HeroBackground />
      <div className="mx-auto flex w-full max-w-[1200px] flex-col items-center px-margin text-center md:px-margin-lg">
        {/* The wordmark bobs gently; each letter lands once on load. */}
        <motion.h1
          id="hero-title"
          aria-label="DatDub"
          className="font-heading text-[clamp(84px,19vw,248px)] leading-[0.9] font-bold tracking-[-0.06em] select-none"
          animate={reduce ? undefined : { y: [0, -14, 0] }}
          transition={{ duration: 6, ease: "easeInOut", repeat: Infinity }}
        >
          {LETTERS.map(({ c, tone }, i) => (
            <motion.span
              key={i}
              aria-hidden="true"
              className={`inline-block ${tone} drop-shadow-[0_18px_40px_rgb(43_71_214/0.18)]`}
              initial={reduce ? false : { opacity: 0, y: 48, rotate: i % 2 ? 4 : -4 }}
              animate={{ opacity: 1, y: 0, rotate: 0 }}
              transition={{ type: "spring", stiffness: 140, damping: 16, delay: 0.1 + i * 0.07 }}
            >
              {c}
            </motion.span>
          ))}
        </motion.h1>

        <motion.div
          className="flex flex-col items-center"
          initial={reduce ? false : { opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut", delay: 0.65 }}
        >
          <p className="mt-6 max-w-[560px] text-body-lg text-ink-muted md:text-[19px] md:leading-[30px]">
            Realistic, connected test databases from a description, CSV files, Postgres or a template. Every row
            checked, every edge case listed.
          </p>
          <Button size="xl" className="mt-9 min-w-44 shadow-lg shadow-primary/25" onClick={onLaunch}>
            Launch studio
            <ArrowRight aria-hidden="true" />
          </Button>
        </motion.div>
      </div>
    </section>
  )
}
