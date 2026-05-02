import { AlertTriangle, Check, Save } from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { api } from "@/shared/api-client"
import { agentsApi } from "@/features/agents/api"
import { projectsApi } from "./api"
import type { Agent } from "@/features/agents/types"
import type { Project } from "./types"

interface Props {
  project: Project
  onSaved: (p: Project) => void
}

export function SpecialistsTab({ project, onSaved }: Props) {
  const { t } = useTranslation("projects")
  const [specialists, setSpecialists] = useState<Agent[]>([])
  const [selected, setSelected] = useState<string[]>(project.allowed_specialists ?? [])
  const [agentlinkOk, setAgentlinkOk] = useState<boolean | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api.get<{ configured: boolean }>("/agentlink/status")
      .then((r) => setAgentlinkOk(r.configured))
      .catch(() => setAgentlinkOk(false))
    agentsApi.list()
      .then((agents) => setSpecialists(agents.filter((a) => a.type === "specialist")))
      .catch(() => {})
  }, [])

  useEffect(() => {
    setSelected(project.allowed_specialists ?? [])
  }, [project.id])

  function toggle(id: string) {
    setSelected((s) => s.includes(id) ? s.filter((x) => x !== id) : [...s, id])
  }

  async function save() {
    setSaving(true)
    try {
      const updated = await projectsApi.update(project.id, { allowed_specialists: selected })
      onSaved(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally { setSaving(false) }
  }

  return (
    <div className="space-y-4">
      <p className="text-[10px] text-zinc-500">{t("specialists.description")}</p>

      {agentlinkOk === false && (
        <div className="flex items-start gap-2 px-3 py-2.5 rounded-md bg-amber-500/[6%] border border-amber-500/20 text-xs text-amber-300">
          <AlertTriangle size={13} className="mt-0.5 flex-shrink-0" />
          {t("specialists.no_agentlink")}
        </div>
      )}

      {specialists.length === 0 ? (
        <p className="text-xs text-zinc-600">{t("specialists.none")}</p>
      ) : (
        <div className="space-y-1">
          {specialists.map((s) => (
            <label key={s.id} className="flex items-center gap-2.5 px-3 py-2 rounded-md hover:bg-white/[3%] cursor-pointer group">
              <input
                type="checkbox"
                checked={selected.includes(s.id)}
                onChange={() => toggle(s.id)}
                className="accent-[var(--hh-accent-from)] w-3.5 h-3.5"
              />
              <span className="text-xs text-zinc-200">{s.name}</span>
              <span className="text-[10px] text-zinc-600 font-mono">{s.id}</span>
            </label>
          ))}
        </div>
      )}

      <button
        onClick={save}
        disabled={saving}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs border transition-colors disabled:opacity-30 ${
          saved
            ? "border-emerald-500/30 text-emerald-400 bg-emerald-500/10"
            : "border-white/[8%] text-zinc-300 hover:text-white hover:bg-white/[5%]"
        }`}
      >
        {saved ? <Check size={12} /> : <Save size={12} />}
        {saved ? t("specialists.saved") : t("specialists.save")}
      </button>
    </div>
  )
}
