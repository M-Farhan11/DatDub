import { Logo } from "@/components/Logo"

const LINKS = [
  { href: "#how-it-works", label: "How it works" },
  { href: "#features", label: "Features" },
  { href: "#privacy", label: "Privacy" },
  { href: "#faq", label: "FAQ" },
]

export function Footer() {
  return (
    <footer className="w-full border-t border-chrome bg-panel">
      <div className="mx-auto flex max-w-[1200px] flex-col gap-4 px-margin py-8 md:flex-row md:items-center md:justify-between md:px-margin-lg">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-4">
          <Logo size={24} textClassName="text-headline-sm" />
          <span className="text-body-sm text-ink-muted">© 2026 DatDub. Realistic test databases.</span>
        </div>
        <nav aria-label="Footer" className="flex flex-wrap gap-x-6 gap-y-2">
          {LINKS.map((link) => (
            <a key={link.href} href={link.href} className="rounded-sm font-heading text-label-md text-ink-muted hover:text-ink">
              {link.label}
            </a>
          ))}
          <a
            href="https://github.com/M-Farhan11/DatDub"
            target="_blank"
            rel="noreferrer"
            className="rounded-sm font-heading text-label-md text-ink-muted hover:text-ink"
          >
            GitHub
          </a>
        </nav>
      </div>
    </footer>
  )
}
