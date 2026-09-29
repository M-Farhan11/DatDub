import type { ComponentProps } from "react"
import { Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"

interface SubmitButtonProps extends ComponentProps<typeof Button> {
  loading: boolean
  loadingLabel: string
}

/** Primary button that shows a spinner and a stage label while a request runs. */
export function SubmitButton({ loading, loadingLabel, children, disabled, ...rest }: SubmitButtonProps) {
  return (
    <Button disabled={disabled || loading} aria-busy={loading} {...rest}>
      {loading && <Loader2 className="animate-spin" aria-hidden="true" />}
      {loading ? loadingLabel : children}
    </Button>
  )
}
