import { Button } from "@/components/ui/button"
import { Logo } from "@/components/Logo"

interface NavbarProps {
  onOpenStudio: () => void
}

export function Navbar({ onOpenStudio }: NavbarProps) {
  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-chrome bg-panel/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 w-full max-w-[1440px] items-center justify-between px-margin md:px-margin-lg">
        <a href="#top" className="rounded-md" aria-label="DatDub home">
          <Logo />
        </a>
        <div className="flex items-center gap-6">
          <nav aria-label="Main" className="hidden items-center gap-6 sm:flex">
            <a
              href="#how-it-works"
              className="rounded-sm font-heading text-label-lg text-ink-muted transition-colors hover:text-ink"
            >
              How it works
            </a>
            <a
              href="https://github.com"
              target="_blank"
              rel="noreferrer"
              className="rounded-sm font-heading text-label-lg text-ink-muted transition-colors hover:text-ink"
            >
              GitHub
            </a>
          </nav>
          <Button onClick={onOpenStudio}>Open studio</Button>
        </div>
      </div>
    </header>
  )
}
