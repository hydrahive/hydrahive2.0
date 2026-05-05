import { useEffect, useState } from "react"
import { llmApi } from "@/features/llm/api"
import { KNOWN_PROVIDERS } from "@/features/llm/_llm_providers"
import { chatApi } from "./api"
import type { Session } from "./types"

interface Props {
  session: Session
  agentDefaultModel: string
  onChanged: (session: Session) => void
}

const RESET_VALUE = "__RESET__"

/** Native <select> für Modellwahl pro Session.
 *  Override pro Session, "Zurück zum Agent-Default" als erste Option. */
export function ModelPicker({ session, agentDefaultModel, onChanged }: Props) {
  const [models, setModels] = useState<string[]>([])
  const [saving, setSaving] = useState(false)

  const override = (session.metadata as { model_override?: string })?.model_override || ""
  const active = override || agentDefaultModel

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
    setSaving(true)
    try {
      const updated = await chatApi.updateSession(session.id, {
        model_override: value === RESET_VALUE ? "" : value,
      })
      onChanged(updated)
    } finally { setSaving(false) }
  }

  return (
    <select
      value={active}
      onChange={handleChange}
      disabled={saving}
      title={override ? `Override aktiv (Default: ${agentDefaultModel})` : "Modell wechseln"}
      className={`appearance-none cursor-pointer px-2 py-0.5 pr-6 rounded font-mono text-xs transition-colors
        bg-no-repeat bg-[length:10px] bg-[position:right_4px_center]
        bg-[url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 24 24%22 fill=%22none%22 stroke=%22%23a78bfa%22 stroke-width=%222%22 stroke-linecap=%22round%22 stroke-linejoin=%22round%22><polyline points=%226 9 12 15 18 9%22/></svg>')]
        ${override
          ? "bg-violet-500/15 text-violet-200 border border-violet-500/30 hover:bg-violet-500/20"
          : "text-violet-300/80 hover:bg-violet-500/10 border border-transparent"
        }`}
    >
      {override && (
        <option value={RESET_VALUE} className="bg-zinc-900 text-zinc-300">
          ↺ Zurück zum Agent-Default ({agentDefaultModel})
        </option>
      )}
      {/* Falls active nicht in models steht (z.B. agent-default mit Custom-Model),
          trotzdem als Option anbieten damit value richtig matcht */}
      {!models.includes(active) && (
        <option value={active} className="bg-zinc-900 text-zinc-300">{active}</option>
      )}
      {models.map((m) => (
        <option key={m} value={m} className="bg-zinc-900 text-zinc-300">
          {m}
        </option>
      ))}
    </select>
  )
}
