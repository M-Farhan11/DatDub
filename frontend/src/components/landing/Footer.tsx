import { Logo } from "@/components/Logo"

export function Footer() {
  return (
    <footer className="w-full border-t border-chrome bg-panel/50 py-6">
      <div className="mx-auto flex w-full max-w-[1440px] flex-col items-center justify-between gap-4 px-margin md:flex-row md:px-margin-lg">
        <Logo size={24} textClassName="text-headline-sm" />
        <p className="text-body-sm text-hint-soft">© 2026 DatDub</p>
        <a
          href="https://github.com"
          target="_blank"
          rel="noreferrer"
          className="rounded-sm font-heading text-label-md text-ink-muted transition-colors hover:text-ink"
        >
          GitHub
        </a>
      </div>
    </footer>
  )
}
