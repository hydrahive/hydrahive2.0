import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import {
  AdminAction,
  AdminFeedback,
  AdminField,
  adminInputClass,
} from "@/features/cockpit/admin/ui"

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
    <div className="space-y-3 border-t border-[#2a364b] pt-3">
      <AdminField
        label={(
          <>
            {t("tailscale.authkey_hint")}{" "}
            <a href={ADMIN_URL} target="_blank" rel="noreferrer" className="text-[#69d7ff] hover:underline">
              login.tailscale.com
            </a>
          </>
        )}
      >
        <input
          ref={inputRef}
          type="password"
          value={authkey}
          onChange={(e) => setAuthkey(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder={t("tailscale.authkey_placeholder")}
          className={`${adminInputClass} font-mono`}
        />
      </AdminField>
      {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
      <div className="flex flex-wrap gap-2">
        <AdminAction onClick={submit} disabled={connecting || !authkey.trim()} tone="primary">
          {connecting ? "…" : t("tailscale.connect")}
        </AdminAction>
        <AdminAction onClick={onCancel} tone="ghost">
          ✕
        </AdminAction>
      </div>
    </div>
  )
}
