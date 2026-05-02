import { Eye, EyeOff } from "lucide-react"
import { useEffect, useState } from "react"
import { credentialsApi } from "./api"
import type { Credential } from "./types"

export function Field({ label, hint, children }: {
  label: string; hint?: string; children: React.ReactNode
}) {
  return (
    <div className="space-y-0.5">
      <label className="block text-[10px] font-medium text-zinc-500">{label}</label>
      {children}
      {hint && <p className="text-[10px] text-zinc-600 mt-0.5">{hint}</p>}
    </div>
  )
}

interface ValueInputProps {
  credential: Credential | null
  value: string
  onChange: (v: string) => void
}

export function CredentialValueInput({ credential, value, onChange }: ValueInputProps) {
  const [showValue, setShowValue] = useState(false)

  useEffect(() => {
    if (credential && showValue && !value) {
      credentialsApi.get(credential.name, true)
        .then((c) => onChange(c.value))
        .catch(() => {})
    }
  }, [credential, showValue, value, onChange])

  return (
    <div className="flex gap-1">
      <input type={showValue ? "text" : "password"} value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={credential?.value_set ? "••••••••" : ""}
        className="flex-1 px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 font-mono" />
      <button type="button" onClick={() => setShowValue(!showValue)}
        className="px-2 py-1 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
        {showValue ? <EyeOff size={11} /> : <Eye size={11} />}
      </button>
    </div>
  )
}
