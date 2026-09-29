import { ClosingCta } from "./ClosingCta"
import { Comparison } from "./Comparison"
import { Faq } from "./Faq"
import { Features } from "./Features"
import { Footer } from "./Footer"
import { Hero } from "./Hero"
import { HowItWorks } from "./HowItWorks"
import { Navbar } from "./Navbar"
import { PrivacyBand } from "./PrivacyBand"
import { ProductPreview } from "./ProductPreview"

interface LandingPageProps {
  onOpenStudio: () => void
  onTryExample: () => void
}

/**
 * Story order: promise (hero) → proof (preview) → why it is different →
 * how it works → capabilities → trust → questions → action.
 */
export function LandingPage({ onOpenStudio, onTryExample }: LandingPageProps) {
  return (
    <div id="top" className="min-h-dvh bg-page">
      <Navbar onOpenStudio={onOpenStudio} />
      <main className="w-full pt-16">
        <Hero onOpenStudio={onOpenStudio} onTryExample={onTryExample} />
        <ProductPreview />
        <Comparison />
        <HowItWorks />
        <Features />
        <PrivacyBand />
        <Faq />
        <ClosingCta onOpenStudio={onOpenStudio} onTryExample={onTryExample} />
      </main>
      <Footer />
    </div>
  )
}
