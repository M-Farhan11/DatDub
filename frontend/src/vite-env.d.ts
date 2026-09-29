/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string
  readonly VITE_USE_FIXTURES?: string
  /** Optional read-only demo connection string for "Use the demo database". Never commit real credentials. */
  readonly VITE_DEMO_DB_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
