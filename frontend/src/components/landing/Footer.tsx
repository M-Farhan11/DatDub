import { Logo } from "@/components/Logo"
import { GITHUB_URL, LANDING_LINKS } from "./links"

/** Logo and copyright left, links right, on every screen size. */
export function Footer() {
  return (
    <footer className="w-full border-t border-chrome bg-panel">
      <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-x-8 gap-y-4 px-margin py-8 md:px-margin-lg">
        <div className="flex flex-col gap-1">
          <Logo size={24} textClassName="text-headline-sm" />
          <span className="text-body-sm text-ink-muted">© 2026 DatDub. Realistic test databases.</span>
        </div>
        <nav aria-label="Footer" className="flex flex-wrap justify-end gap-x-6 gap-y-2">
          {[...LANDING_LINKS, { href: GITHUB_URL, label: "GitHub" }].map((link) => (
            <a
              key={link.href}
              href={link.href}
              {...(link.href.startsWith("http") ? { target: "_blank", rel: "noreferrer" } : {})}
              className="rounded-sm font-heading text-label-md text-ink-muted hover:text-ink"
            >
              {link.label}
            </a>
          ))}
        </nav>
      </div>
    </footer>
  )
}
