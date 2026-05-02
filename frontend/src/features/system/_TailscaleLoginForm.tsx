import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"

const ADMIN_URL = "https://login.tailscale.com/admin/settings/keys"

interface Props {
  connecting: boolean
  error: string | null
  onConnect: (key: string) => void
  onCancel: () => void
}

export function TailscaleLoginForm({ connecting, error, onConnect, onCancel }: Props) {
  const { t } = useTranslation("system")
  const [authkey, setAuthkey] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { setTimeout(() => inputRef.current?.focus(), 50) }, [])

  function submit() {
    if (authkey.trim()) onConnect(authkey.trim())
  }

  return (
    <div className="space-y-2 pt-1 border-t border-white/[6%]">
      <p className="text-[11px] text-zinc-500">{t("tailscale.authkey_hint")}{" "}
        <a href={ADMIN_URL} target="_blank" rel="noreferrer" className="text-violet-400 hover:underline">
          login.tailscale.com
        </a>
      </p>
      {error && <p className="text-xs text-rose-400">{error}</p>}
      <div className="flex gap-2">
        <input ref={inputRef} type="password" value={authkey}
          onChange={(e) => setAuthkey(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder={t("tailscale.authkey_placeholder")}
          className="flex-1 px-3 py-1.5 rounded-lg bg-zinc-900 border border-white/[8%] text-zinc-200 text-sm font-mono placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-emerald-500/40" />
        <button onClick={submit} disabled={connecting || !authkey.trim()}
          className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium disabled:opacity-40 transition-colors">
          {connecting ? "…" : t("tailscale.connect")}
        </button>
        <button onClick={onCancel}
          className="px-3 py-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-white/5 text-sm transition-colors">
          ✕
        </button>
      </div>
    </div>
  )
}
