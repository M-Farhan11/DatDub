import { ClosingCta } from "./ClosingCta"
import { Footer } from "./Footer"
import { Hero } from "./Hero"
import { HowItWorks } from "./HowItWorks"
import { Navbar } from "./Navbar"
import { ProductPreview } from "./ProductPreview"

interface LandingPageProps {
  onOpenStudio: () => void
  onTryExample: () => void
}

export function LandingPage({ onOpenStudio, onTryExample }: LandingPageProps) {
  return (
    <div id="top" className="min-h-dvh bg-page">
      <Navbar onOpenStudio={onOpenStudio} />
      <main className="w-full pt-16">
        <Hero onOpenStudio={onOpenStudio} onTryExample={onTryExample} />
        <ProductPreview />
        <HowItWorks />
        <ClosingCta onOpenStudio={onTryExample} />
      </main>
      <Footer />
    </div>
  )
}
