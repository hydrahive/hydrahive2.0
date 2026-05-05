import { useEffect, useState } from "react"
import { llmApi } from "@/features/llm/api"
import { KNOWN_PROVIDERS } from "@/features/llm/_llm_providers"

interface Props {
  /** Aktuelles Modell — wird im select selektiert dargestellt. */
  current: string
  /** Optional: Default-Hinweis (z.B. Agent-Default), wird im title angezeigt. */
  hint?: string
  /** Wird gerufen mit dem neuen Modell. null = "zurücksetzen" wenn supportet. */
  onPick: (model: string) => Promise<void> | void
  /** Wenn true: extra "↺ Reset"-Option am Anfang anbieten. */
  showReset?: boolean
  /** onPick(null) Reset-Handler — nur wenn showReset=true. */
  onReset?: () => Promise<void> | void
}

const RESET_VALUE = "__RESET__"

/** Native <select> für Modellwahl. Caller entscheidet wo der Pick hingeht
 *  (session.metadata.model_override im Chat, agent.llm_model im Buddy). */
export function ModelPicker({ current, hint, onPick, showReset, onReset }: Props) {
  const [models, setModels] = useState<string[]>([])
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let alive = true
    llmApi.getConfig()
      .then((cfg) => {
        if (!alive) return
        const stored = new Set(cfg.providers.flatMap((p) => p.models))
        const configuredIds = new Set(
          cfg.providers
            .filter((p) => !!p.api_key || !!(p as { oauth?: { access?: string } }).oauth?.access)
            .map((p) => p.id),
        )
        for (const known of KNOWN_PROVIDERS) {
          if (configuredIds.has(known.id)) {
            for (const m of known.models) stored.add(m)
          }
        }
        setModels(Array.from(stored).sort())
      })
      .catch(() => {})
    return () => { alive = false }
  }, [])

  async function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const value = e.target.value
    setBusy(true)
    try {
      if (value === RESET_VALUE) {
        await onReset?.()
      } else if (value !== current) {
        await onPick(value)
      }
    } finally { setBusy(false) }
  }

  return (
    <select
      value={current}
      onChange={handleChange}
      disabled={busy}
      title={hint || "Modell wechseln"}
      className="appearance-none cursor-pointer px-2 py-0.5 pr-6 rounded font-mono text-xs transition-colors
        bg-no-repeat bg-[length:10px] bg-[position:right_4px_center]
        bg-[url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 24 24%22 fill=%22none%22 stroke=%22%23a78bfa%22 stroke-width=%222%22 stroke-linecap=%22round%22 stroke-linejoin=%22round%22><polyline points=%226 9 12 15 18 9%22/></svg>')]
        bg-violet-500/15 text-violet-200 border border-violet-500/30 hover:bg-violet-500/20"
    >
      {showReset && (
        <option value={RESET_VALUE} className="bg-zinc-900 text-zinc-300">
          ↺ Reset auf Agent-Default
        </option>
      )}
      {!models.includes(current) && current && (
        <option value={current} className="bg-zinc-900 text-zinc-300">{current}</option>
      )}
      {models.map((m) => (
        <option key={m} value={m} className="bg-zinc-900 text-zinc-300">{m}</option>
      ))}
    </select>
  )
}
