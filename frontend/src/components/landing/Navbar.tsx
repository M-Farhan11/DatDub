import { Button } from "@/components/ui/button"
import { Logo } from "@/components/Logo"

interface NavbarProps {
  onOpenStudio: () => void
}

const LINKS = [
  { href: "#how-it-works", label: "How it works" },
  { href: "#features", label: "Features" },
  { href: "#privacy", label: "Privacy" },
  { href: "#faq", label: "FAQ" },
]

export function Navbar({ onOpenStudio }: NavbarProps) {
  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-chrome bg-panel/85 backdrop-blur-xl">
      <div className="mx-auto flex h-16 w-full max-w-[1200px] items-center justify-between gap-6 px-margin md:px-margin-lg">
        <a href="#top" className="rounded-md" aria-label="DatDub home">
          <Logo size={30} textClassName="text-[22px]" />
        </a>
        <nav aria-label="Main" className="hidden items-center gap-7 md:flex">
          {LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="rounded-sm font-heading text-label-lg text-ink-muted transition-colors hover:text-ink"
            >
              {link.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-4">
          <a
            href="https://github.com/M-Farhan11/DatDub"
            target="_blank"
            rel="noreferrer"
            className="hidden rounded-sm font-heading text-label-lg text-ink-muted transition-colors hover:text-ink sm:inline"
          >
            GitHub
          </a>
          <Button onClick={onOpenStudio}>Open studio</Button>
        </div>
      </div>
    </header>
  )
}
