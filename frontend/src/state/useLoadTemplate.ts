import { useCallback, useState } from "react"
import { errorMessage, getTemplate } from "@/api/client"
import { useStudio } from "./useStudio"

/** Loads a template schema and jumps to the Schema step. */
export function useLoadTemplate() {
  const { dispatch } = useStudio()
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(
    async (id: string) => {
      setLoadingId(id)
      setError(null)
      try {
        const schema = await getTemplate(id)
        dispatch({ type: "schemaLoaded", schema, kind: "template" })
      } catch (err) {
        setError(errorMessage(err))
      } finally {
        setLoadingId(null)
      }
    },
    [dispatch],
  )

  return { load, loadingId, error, clearError: () => setError(null) }
}
