import { Check, Download, Save } from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { agentsApi } from "./api"
import type { Agent } from "./types"

const COMPONENTS = ["identity", "behavior", "background"] as const
type Component = typeof COMPONENTS[number]

interface Props {
  agent: Agent
}

export function SoulTab({ agent }: Props) {
  const { t } = useTranslation("agents")
  const [soul, setSoul] = useState<Record<Component, string>>({ identity: "", behavior: "", background: "" })
  const [saved, setSaved] = useState<Record<Component, boolean>>({ identity: false, behavior: false, background: false })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    agentsApi.getSoul(agent.id)
      .then((r) => setSoul(r.components as Record<Component, string>))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [agent.id])

  async function saveComponent(c: Component) {
    await agentsApi.setSoulComponent(agent.id, c, soul[c])
    setSaved((s) => ({ ...s, [c]: true }))
    setTimeout(() => setSaved((s) => ({ ...s, [c]: false })), 2000)
  }

  async function loadTemplate() {
    const r = await agentsApi.getSoulTemplates(agent.id)
    setSoul((prev) => ({
      ...prev,
      ...Object.fromEntries(
        Object.entries(r.templates).map(([k, v]) => [k, prev[k as Component] || v])
      ) as Record<Component, string>,
    }))
  }

  const labels: Record<Component, string> = {
    identity: t("soul.identity"),
    behavior: t("soul.behavior"),
    background: t("soul.background"),
  }
  const hints: Record<Component, string> = {
    identity: t("soul.identity_hint"),
    behavior: t("soul.behavior_hint"),
    background: t("soul.background_hint"),
  }

  if (loading) return <div className="text-xs text-zinc-500 py-4">{t("soul.loading")}</div>

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <p className="text-[10px] text-zinc-500">{t("soul.description")}</p>
        <button
          onClick={loadTemplate}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] border border-white/[8%] text-zinc-400 hover:text-zinc-200 hover:bg-white/[5%] transition-colors"
        >
          <Download size={11} /> {t("soul.load_template")}
        </button>
      </div>

      {COMPONENTS.map((c) => (
        <div key={c} className="space-y-1">
          <div className="flex items-center justify-between">
            <div>
              <label className="block text-[10px] font-medium text-zinc-400">{labels[c]}</label>
              <span className="block text-[10px] text-zinc-600">{hints[c]}</span>
            </div>
            <button
              onClick={() => saveComponent(c)}
              className={`flex items-center gap-1 px-2 py-1 rounded-md text-[11px] border transition-colors ${
                saved[c]
                  ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
                  : "border-white/[8%] text-zinc-400 hover:text-zinc-200 hover:bg-white/[5%]"
              }`}
            >
              {saved[c] ? <Check size={11} /> : <Save size={11} />}
              {saved[c] ? t("soul.saved") : t("soul.save_component")}
            </button>
          </div>
          <textarea
            value={soul[c]}
            onChange={(e) => setSoul((s) => ({ ...s, [c]: e.target.value }))}
            rows={c === "background" ? 6 : 8}
            placeholder={soul[c] ? undefined : t("soul.empty_hint")}
            className="w-full px-2 py-1.5 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 font-mono leading-relaxed focus:outline-none focus:ring-1 focus:ring-[var(--hh-accent-from)]/50 placeholder:text-zinc-700"
          />
        </div>
      ))}
    </div>
  )
}
