import { useState } from "react"
import { Database } from "lucide-react"
import { dbTables, errorMessage } from "@/api/client"
import type { DbConnection, DbTableInfo } from "@/api/types"
import { ErrorCallout } from "@/components/shared/ErrorCallout"
import { Field } from "@/components/shared/Field"
import { SegmentedControl } from "@/components/shared/SegmentedControl"
import { SubmitButton } from "@/components/shared/SubmitButton"
import { Button } from "@/components/ui/button"
import { monoInputClass, textInputClass } from "@/lib/styles"
import { DbConnectHelp } from "./DbConnectHelp"
import { PasswordInput } from "./PasswordInput"

type Method = "url" | "fields" | "sqlite"

const METHODS = [
  { value: "url" as const, label: "Connection string" },
  { value: "fields" as const, label: "Fields" },
  { value: "sqlite" as const, label: "Upload SQLite file" },
]

const DEMO_URL = import.meta.env.VITE_DEMO_DB_URL?.trim() || null

interface DbConnectFormProps {
  onConnected: (connection: DbConnection, tables: DbTableInfo[]) => void
  onSqlite: (file: File) => void
}

export function DbConnectForm({ onConnected, onSqlite }: DbConnectFormProps) {
  const [method, setMethod] = useState<Method>("url")
  const [url, setUrl] = useState("")
  const [host, setHost] = useState("")
  const [port, setPort] = useState("5432")
  const [database, setDatabase] = useState("")
  const [user, setUser] = useState("")
  const [password, setPassword] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const urlValid = /^postgres(ql)?:\/\//i.test(url.trim())
  const fieldsValid = host.trim() !== "" && database.trim() !== "" && user.trim() !== "" && Number(port) > 0
  const ready = method === "url" ? urlValid : method === "fields" ? fieldsValid : file !== null

  const buildConnection = (): DbConnection =>
    method === "url"
      ? { url: url.trim() }
      : {
          host: host.trim(),
          port: Number(port),
          database: database.trim(),
          user: user.trim(),
          password: password || null,
          sslmode: "require",
        }

  const connect = async () => {
    if (method === "sqlite") {
      if (file) onSqlite(file)
      return
    }
    setLoading(true)
    setError(null)
    const connection = buildConnection()
    try {
      const res = await dbTables(connection)
      onConnected(connection, res.tables)
    } catch (err) {
      setError(errorMessage(err))
      setLoading(false)
    }
  }

  const useDemo = () => {
    if (!DEMO_URL) return
    setMethod("url")
    setUrl(DEMO_URL)
    setError(null)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SegmentedControl label="How to connect" options={METHODS} value={method} onChange={setMethod} disabled={loading} />
        {DEMO_URL && method !== "sqlite" && (
          <Button variant="ghost" size="sm" onClick={useDemo} disabled={loading}>
            <Database aria-hidden="true" />
            Use the demo database
          </Button>
        )}
      </div>

      {method === "url" && (
        <Field
          id="db-url"
          label="Connection string"
          error={url.trim() !== "" && !urlValid ? "Use a Postgres URL that starts with postgresql://" : null}
          hint="Postgres and Supabase are supported. The connection is opened read-only and never stored."
        >
          <PasswordInput
            id="db-url"
            value={url}
            onChange={setUrl}
            disabled={loading}
            subject="connection string"
            placeholder="postgresql://user:password@host:5432/database"
            inputClassName={monoInputClass}
          />
        </Field>
      )}

      {method === "fields" && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-6">
          <Field id="db-host" label="Host" className="sm:col-span-4">
            <input
              id="db-host"
              value={host}
              onChange={(e) => setHost(e.target.value)}
              disabled={loading}
              autoComplete="off"
              spellCheck={false}
              placeholder="db.example.supabase.co"
              className={monoInputClass}
            />
          </Field>
          <Field id="db-port" label="Port" className="sm:col-span-2">
            <input
              id="db-port"
              inputMode="numeric"
              value={port}
              onChange={(e) => setPort(e.target.value.replace(/\D/g, ""))}
              disabled={loading}
              className={monoInputClass}
            />
          </Field>
          <Field id="db-name" label="Database" className="sm:col-span-2">
            <input
              id="db-name"
              value={database}
              onChange={(e) => setDatabase(e.target.value)}
              disabled={loading}
              autoComplete="off"
              spellCheck={false}
              placeholder="postgres"
              className={monoInputClass}
            />
          </Field>
          <Field id="db-user" label="User" className="sm:col-span-2">
            <input
              id="db-user"
              value={user}
              onChange={(e) => setUser(e.target.value)}
              disabled={loading}
              autoComplete="off"
              spellCheck={false}
              placeholder="datdub_reader"
              className={monoInputClass}
            />
          </Field>
          <Field id="db-password" label="Password" className="sm:col-span-2">
            <PasswordInput
              id="db-password"
              value={password}
              onChange={setPassword}
              disabled={loading}
              subject="password"
              inputClassName={textInputClass}
            />
          </Field>
          <p className="text-body-sm text-ink-muted sm:col-span-6">
            The connection uses SSL and is opened read-only. Credentials stay in this browser tab and are never stored.
          </p>
        </div>
      )}

      {method === "sqlite" && (
        <Field id="db-sqlite" label="SQLite database file" hint="Accepts .sqlite, .sqlite3 and .db files. The file is deleted after it is read.">
          <input
            id="db-sqlite"
            type="file"
            accept=".sqlite,.sqlite3,.db"
            disabled={loading}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-body-md text-ink-muted file:mr-4 file:h-9 file:cursor-pointer file:rounded-full file:border file:border-line file:bg-card file:px-4 file:font-heading file:text-label-lg file:font-medium file:text-primary-deep hover:file:border-primary"
          />
        </Field>
      )}

      {error && <ErrorCallout title="Could not connect" message={error} />}

      <div className="flex justify-end">
        <SubmitButton loading={loading} loadingLabel="Connecting…" disabled={!ready} onClick={connect}>
          {method === "sqlite" ? "Continue" : "Connect"}
        </SubmitButton>
      </div>

      <DbConnectHelp />
    </div>
  )
}
