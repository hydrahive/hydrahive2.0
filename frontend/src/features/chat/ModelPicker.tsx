import { useEffect, useRef, useState } from "react"
import { ChevronDown, RotateCcw } from "lucide-react"
import { llmApi } from "@/features/llm/api"
import { KNOWN_PROVIDERS } from "@/features/llm/_llm_providers"
import { chatApi } from "./api"
import type { Session } from "./types"

interface Props {
  session: Session
  agentDefaultModel: string
  onChanged: (session: Session) => void
}

/** Pill im Chat-Header: zeigt das aktive Modell, Klick = Dropdown.
 *  Override pro Session, Reset stellt zurück auf Agent-Default. */
export function ModelPicker({ session, agentDefaultModel, onChanged }: Props) {
  const [open, setOpen] = useState(false)
  const [models, setModels] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const override = (session.metadata as { model_override?: string })?.model_override || ""
  const active = override || agentDefaultModel

  useEffect(() => {
    if (!open) return
    llmApi.getConfig()
      .then((cfg) => {
        // Gespeicherte Modelle in llm.json
        const stored = new Set(cfg.providers.flatMap((p) => p.models))
        // Zusätzlich: alle KNOWN-Modelle der konfigurierten Provider
        // (Provider gilt als konfiguriert wenn api_key oder oauth-Block vorhanden)
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
  }, [open])

  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [open])

  async function pick(model: string | null) {
    setSaving(true)
    try {
      const updated = await chatApi.updateSession(session.id, {
        model_override: model ?? "",  // "" → Backend entfernt den Override
      })
      onChanged(updated)
      setOpen(false)
    } finally { setSaving(false) }
  }

  return (
    <div className="relative inline-block" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        disabled={saving}
        className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded font-mono text-xs transition-colors ${
          override
            ? "bg-violet-500/15 text-violet-200 border border-violet-500/30 hover:bg-violet-500/20"
            : "text-violet-300/80 hover:bg-violet-500/10"
        }`}
        title={override ? `Override aktiv (Default: ${agentDefaultModel})` : "Modell wechseln"}
      >
        {active}
        <ChevronDown size={10} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 w-72 rounded-lg bg-zinc-950 border border-white/10 shadow-2xl z-50 overflow-hidden">
          <div className="px-3 py-1.5 text-[10px] uppercase tracking-widest text-zinc-500 border-b border-white/5">
            Modell für diese Session
          </div>
          <div className="max-h-72 overflow-y-auto">
            {override && (
              <button
                onClick={() => pick(null)}
                className="w-full text-left px-3 py-1.5 text-xs text-zinc-400 hover:bg-white/5 flex items-center gap-2 border-b border-white/5"
              >
                <RotateCcw size={11} /> Zurück zum Agent-Default ({agentDefaultModel})
              </button>
            )}
            {models.length === 0 && (
              <p className="px-3 py-3 text-xs text-zinc-600">
                Keine Modelle konfiguriert — siehe /llm
              </p>
            )}
            {models.map((m) => (
              <button
                key={m}
                onClick={() => pick(m)}
                className={`w-full text-left px-3 py-1.5 text-xs font-mono transition-colors ${
                  m === active
                    ? "bg-violet-500/15 text-violet-200"
                    : "text-zinc-300 hover:bg-white/5"
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
