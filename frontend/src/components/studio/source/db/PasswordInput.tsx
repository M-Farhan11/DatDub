import { useState } from "react"
import { Eye, EyeOff } from "lucide-react"
import { cn } from "@/lib/utils"

interface PasswordInputProps {
  id: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
  mono?: boolean
  /** Name read by the show/hide button, e.g. "connection string". */
  subject: string
  inputClassName: string
}

/** Masked input with a show/hide toggle. Never autocompletes. */
export function PasswordInput({ id, value, onChange, placeholder, disabled, subject, inputClassName }: PasswordInputProps) {
  const [visible, setVisible] = useState(false)
  return (
    <div className="relative">
      <input
        id={id}
        type={visible ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete="off"
        spellCheck={false}
        className={cn(inputClassName, "pr-11")}
      />
      <button
        type="button"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? `Hide ${subject}` : `Show ${subject}`}
        aria-pressed={visible}
        className="absolute top-1/2 right-1.5 flex size-8 -translate-y-1/2 items-center justify-center rounded-full text-ink-muted hover:bg-surface-low hover:text-ink"
      >
        {visible ? <EyeOff className="size-4" aria-hidden="true" /> : <Eye className="size-4" aria-hidden="true" />}
      </button>
    </div>
  )
}
