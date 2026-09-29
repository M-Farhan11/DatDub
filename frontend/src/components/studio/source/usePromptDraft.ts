import { useState } from "react"
import { errorMessage, schemaFromPrompt } from "@/api/client"
import { useStudio } from "@/state/useStudio"
import { MIN_PROMPT_LENGTH } from "./promptExamples"

/** Prompt text + "Draft schema" request, shared by the source picker and the Describe screen. */
export function usePromptDraft() {
  const { dispatch } = useStudio()
  const [prompt, setPrompt] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = prompt.trim().length >= MIN_PROMPT_LENGTH && !loading

  const submit = async () => {
    if (!canSubmit) return
    setLoading(true)
    setError(null)
    try {
      const res = await schemaFromPrompt(prompt.trim())
      dispatch({ type: "schemaLoaded", schema: res.schema, kind: "prompt", notes: res.notes })
    } catch (err) {
      setError(errorMessage(err))
      setLoading(false)
    }
  }

  return { prompt, setPrompt, loading, error, canSubmit, submit }
}
