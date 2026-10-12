import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { LockKeyhole, LockKeyholeOpen } from "lucide-react"
import { type VaultStatus, vaultApi } from "./api"
import { useVaultStore } from "./vaultStore"
import { lockNow, minutesLeft } from "./vaultActions"

const POLL_MS = 30_000   // /vault/status liest nur (verlängert die Entsperrung NICHT) → Abfragen ist harmlos

export function VaultBadgeView({ status, onLock }: { status: VaultStatus | null; onLock: () => void }) {
  const { t } = useTranslation("vault")
  if (!status?.pin_set) return null
  if (!status.unlocked) {
    return (
      <span className="inline-flex items-center gap-1 rounded-[4px] border border-[#2a364b] px-2 py-1 text-xs text-[#8d9ab0]" title={t("locked")}>
        <LockKeyhole size={13} />{t("locked")}
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-2 rounded-[4px] border border-[#69d7ff]/40 bg-[#69d7ff]/10 px-2 py-1 text-xs text-[#69d7ff]">
      <LockKeyholeOpen size={13} />
      {t("unlocked_for", { min: minutesLeft(status.remaining_seconds) })}
      <button type="button" onClick={onLock} className="font-semibold underline-offset-2 hover:underline">{t("lock_now")}</button>
    </span>
  )
}

/** Kopfleiste: Vault-Zustand mit Restzeit und „Jetzt sperren“ (docs/specs/vault.md §4.3). */
export function VaultBadge() {
  const token = useVaultStore((s) => s.token)
  const [status, setStatus] = useState<VaultStatus | null>(null)

  useEffect(() => {
    let alive = true
    const load = () => { vaultApi.status().then((s) => { if (alive) setStatus(s) }).catch(() => {}) }
    load()
    const id = window.setInterval(load, POLL_MS)
    return () => { alive = false; window.clearInterval(id) }
  }, [token])

  async function onLock() {
    await lockNow()
    setStatus((s) => (s ? { ...s, unlocked: false, remaining_seconds: 0 } : s))
    window.location.reload()                                  // offene Vault-Seiten sofort schließen
  }
  return <VaultBadgeView status={status} onLock={() => void onLock()} />
}
