import { Button } from "@/components/ui/button"

interface ClosingCtaProps {
  onOpenStudio: () => void
}

export function ClosingCta({ onOpenStudio }: ClosingCtaProps) {
  return (
    <section
      aria-labelledby="closing-title"
      className="flex w-full flex-col items-center px-margin py-24 text-center md:px-margin-lg md:py-28"
    >
      <h2
        id="closing-title"
        className="font-heading text-headline-lg font-medium text-ink md:text-[28px] md:leading-9"
      >
        Try it with the finance example.
      </h2>
      <Button size="xl" className="mt-6" onClick={onOpenStudio}>
        Open studio
      </Button>
    </section>
  )
}
