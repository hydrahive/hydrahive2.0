import { useState } from "react"
import { useTranslation } from "react-i18next"
import { chatApi } from "@/features/chat/api"
import { BUDDY_MODES, type BuddyMode } from "./api"

/** Gesprächsmodus der aktuellen Buddy-Session. Speichert pro Session
 *  (session.metadata.buddy_mode); der Runner hängt den passenden Stil-Hinweis
 *  an den Buddy-Prompt. Kein LLM-Aufruf beim Umschalten.
 *  Der Aufrufer setzt `key={sessionId}` — neue Session = frischer State. */
export function BuddyModeSelect({ sessionId, initial }: { sessionId: string; initial: BuddyMode }) {
  const { t } = useTranslation("buddy")
  const [mode, setMode] = useState<BuddyMode>(initial)
  const [error, setError] = useState(false)

  async function change(next: BuddyMode) {
    const previous = mode
    setMode(next)
    setError(false)
    try {
      await chatApi.updateSession(sessionId, { buddy_mode: next })
    } catch {
      setMode(previous)
      setError(true)
    }
  }

  return (
    <>
      <label htmlFor="buddy-mode" className="block text-xs font-bold uppercase tracking-[0.12em] text-[#69d7ff]">{t("mode.label")}</label>
      <select
        id="buddy-mode"
        value={mode}
        onChange={(e) => void change(e.target.value as BuddyMode)}
        className="w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2 text-sm text-[#e8eef8]"
      >
        {BUDDY_MODES.map((m) => <option key={m} value={m}>{t(`mode.${m}`)}</option>)}
      </select>
      <p className={`text-xs ${error ? "text-rose-400" : "text-[#8d9ab0]"}`}>{error ? t("mode.error") : t("mode.hint")}</p>
    </>
  )
}
