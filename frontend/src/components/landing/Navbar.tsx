import { Button } from "@/components/ui/button"
import { Logo } from "@/components/Logo"
import { LANDING_LINKS } from "./links"

interface NavbarProps {
  onLaunch: () => void
}

/** Logo left, section links truly centered (3-column grid), launch button far right. */
export function Navbar({ onLaunch }: NavbarProps) {
  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-chrome/70 bg-panel/80 backdrop-blur-xl">
      <div className="mx-auto grid h-16 w-full max-w-[1200px] grid-cols-[1fr_auto] items-center gap-6 px-margin md:grid-cols-[1fr_auto_1fr] md:px-margin-lg">
        <a href="#top" className="justify-self-start rounded-md" aria-label="DatDub home">
          <Logo size={30} textClassName="text-[22px]" />
        </a>
        <nav aria-label="Main" className="hidden items-center gap-8 md:flex">
          {LANDING_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="rounded-sm font-heading text-label-lg text-ink-muted transition-colors hover:text-ink"
            >
              {link.label}
            </a>
          ))}
        </nav>
        <Button className="justify-self-end" onClick={onLaunch}>
          Launch studio
        </Button>
      </div>
    </header>
  )
}
