import { useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { areasApi } from "./api"
import { MAX_PURPOSE, PurposeView, resolveSuggestions, type Resolved } from "./PurposeView"
import type { AreaCatalog } from "./types"

interface Props { agentId: string; catalog: AreaCatalog; lang: string; onApply: (areaIds: string[]) => void }

/** Zweck-Vorschlag (AB5, Frontend): nur Vorauswahl. Es ändert sich nichts, bis „Übernehmen“ und danach der normale Speichern-Knopf. */
export function PurposeSuggest({ agentId, catalog, lang, onApply }: Props) {
  const { t } = useTranslation("agents")
  const { t: tErr } = useTranslation("errors")
  const [purpose, setPurpose] = useState("")
  const [busy, setBusy] = useState(false)
  const inFlight = useRef(false)              // Doppelklick im selben Tick (Review #794)
  const [suggestions, setSuggestions] = useState<Resolved[]>([])
  const [picked, setPicked] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  async function suggest() {
    if (busy || inFlight.current) return
    inFlight.current = true
    setBusy(true); setError(null); setSuggestions([]); setPicked([])
    try {
      const res = await areasApi.suggest(agentId, purpose.trim().slice(0, MAX_PURPOSE), lang)
      const resolved = resolveSuggestions(res.suggestions, catalog)
      setSuggestions(resolved); setPicked(resolved.map((r) => r.area.id))
      if (res.error === "llm_failed") setError(tErr("llm_failed"))                 // übersetzt, nie Rohtext
      else if (resolved.length === 0) setError(t("areas.purpose_none"))
    } catch (e) {
      const status = (e as { status?: number } | null)?.status
      setError(status === 403 ? t("areas.purpose_forbidden") : tErr("llm_failed"))   // defensiv, nie Rohtext des Servers
    } finally { setBusy(false); inFlight.current = false }
  }

  return (
    <PurposeView
      purpose={purpose} onPurpose={setPurpose} onSuggest={suggest} busy={busy} suggestions={suggestions} picked={picked} error={error}
      onToggle={(id) => setPicked((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]))}
      onApply={() => { onApply(picked); setSuggestions([]); setPicked([]) }}
    />
  )
}
