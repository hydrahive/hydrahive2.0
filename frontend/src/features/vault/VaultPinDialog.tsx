import { useState } from "react"
import { useTranslation } from "react-i18next"
import { LockKeyhole } from "lucide-react"
import { pinValid, vaultApi } from "./api"
import { useVaultStore } from "./vaultStore"

type Mode = "unlock" | "setup" | "forgot"

/** Globaler PIN-Dialog: erscheint, sobald ein Vault-Bereich 423 meldet (docs/specs/vault.md §4.2–4.4). */
export function VaultPinDialog() {
  const { t } = useTranslation("vault")
  const prompt = useVaultStore((s) => s.prompt)
  const [mode, setMode] = useState<Mode | null>(null)
  const [pin, setPin] = useState("")
  const [pin2, setPin2] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  if (!prompt) return null
  const m: Mode = mode ?? (prompt.pinSet ? "unlock" : "setup")

  function close() {
    useVaultStore.getState().closePrompt()
    setMode(null); setPin(""); setPin2(""); setPassword(""); setError("")
  }

  async function submit() {
    setError("")
    if (m !== "unlock" && pin !== pin2) return setError(t("pin_mismatch"))
    if (!pinValid(pin)) return setError(t("pin_format"))
    setBusy(true)
    try {
      const r = m === "unlock" ? await vaultApi.unlock(pin)
        : m === "setup" ? await vaultApi.setup(password, pin) : await vaultApi.reset(password, pin)
      useVaultStore.getState().setToken(r.vault_token)
      close()
      window.location.reload()                                  // gesperrte Seite neu laden, jetzt mit Token
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const input = "w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-center text-lg tracking-[0.3em] text-[#e8eef8]"
  return (
    <div className="fixed inset-0 z-[100] grid place-items-center bg-black/70 p-4" role="dialog" aria-modal="true">
      <form onSubmit={(e) => { e.preventDefault(); void submit() }}
        className="w-full max-w-sm space-y-3 rounded-[6px] border border-[#69d7ff]/40 bg-[#111827] p-5 shadow-2xl">
        <div className="flex items-center gap-2">
          <LockKeyhole size={18} className="text-[#69d7ff]" />
          <h2 className="text-base font-bold text-[#e8eef8]">{t(`title_${m}`)}</h2>
        </div>
        <p className="text-xs leading-5 text-[#8d9ab0]">{t(`text_${m}`)}</p>
        {m !== "unlock" && (
          <input type="password" autoComplete="current-password" value={password} placeholder={t("password")}
            onChange={(e) => setPassword(e.target.value)} className={input.replace("text-center text-lg tracking-[0.3em]", "text-sm")} />
        )}
        <input type="password" inputMode="numeric" autoComplete="off" autoFocus value={pin} maxLength={12}
          placeholder={m === "unlock" ? t("pin") : t("new_pin")} onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} className={input} />
        {m !== "unlock" && (
          <input type="password" inputMode="numeric" autoComplete="off" value={pin2} maxLength={12} placeholder={t("repeat_pin")}
            onChange={(e) => setPin2(e.target.value.replace(/\D/g, ""))} className={input} />
        )}
        {error && <p className="text-xs text-rose-300">{error}</p>}
        <div className="flex items-center justify-between gap-2 pt-1">
          {m === "unlock"
            ? <button type="button" onClick={() => { setMode("forgot"); setError("") }} className="text-xs text-[#8d9ab0] hover:text-[#e8eef8]">{t("forgot")}</button>
            : <span />}
          <div className="flex gap-2">
            <button type="button" onClick={close} className="rounded-[4px] px-3 py-1.5 text-sm text-[#8d9ab0] hover:text-[#e8eef8]">{t("cancel")}</button>
            <button type="submit" disabled={busy} className="rounded-[4px] border border-[#69d7ff]/50 bg-[#69d7ff]/15 px-3 py-1.5 text-sm font-semibold text-[#69d7ff] disabled:opacity-40">
              {t(m === "unlock" ? "unlock" : "save")}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
