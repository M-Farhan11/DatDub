import { ChevronDown } from "lucide-react"
import { CopyButton } from "@/components/shared/CopyButton"

const READONLY_SQL = `CREATE ROLE datdub_reader LOGIN PASSWORD 'choose-a-strong-password';
GRANT CONNECT ON DATABASE your_database TO datdub_reader;
GRANT USAGE ON SCHEMA public TO datdub_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO datdub_reader;`

/** Collapsible help: read-only user + localhost note. */
export function DbConnectHelp() {
  return (
    <details className="group rounded-xl border border-line bg-surface-low">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 rounded-xl px-4 py-3 font-heading text-label-lg font-medium text-ink [&::-webkit-details-marker]:hidden">
        How to connect safely
        <ChevronDown className="size-4 text-ink-muted transition-transform group-open:rotate-180" aria-hidden="true" />
      </summary>
      <div className="space-y-4 border-t border-line px-4 py-4 text-body-md text-ink-muted">
        <div>
          <p className="font-medium text-ink">Use a read-only user</p>
          <p className="mt-1">
            DatDub only reads, inside a read-only transaction, but a user that can only read is the safest choice.
            Run this in your database, then connect with that user:
          </p>
          <pre className="mt-3 overflow-x-auto rounded-lg border border-line bg-card p-3 font-mono text-code-sm text-ink">
            {READONLY_SQL}
          </pre>
          <div className="mt-2">
            <CopyButton text={READONLY_SQL} label="Copy SQL" />
          </div>
        </div>
        <div>
          <p className="font-medium text-ink">Databases on localhost</p>
          <p className="mt-1">
            A database on localhost is not reachable from the website. Use a tunnel (for example ngrok or Cloudflare
            Tunnel) or run DatDub locally.
          </p>
        </div>
      </div>
    </details>
  )
}
