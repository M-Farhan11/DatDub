import { Faq } from "./Faq"
import { Features } from "./Features"
import { Footer } from "./Footer"
import { Hero } from "./Hero"
import { HowItWorks } from "./HowItWorks"
import { Navbar } from "./Navbar"
import { PrivacyBand } from "./PrivacyBand"

interface LandingPageProps {
  onLaunch: () => void
}

/** Story order: the name (hero) → how it works → what it does → why it is safe → questions. */
export function LandingPage({ onLaunch }: LandingPageProps) {
  return (
    <div id="top" className="min-h-dvh bg-page">
      <Navbar onLaunch={onLaunch} />
      <main className="w-full pt-16">
        <Hero onLaunch={onLaunch} />
        <HowItWorks />
        <Features />
        <PrivacyBand />
        <Faq />
      </main>
      <Footer />
    </div>
  )
}
