import { useEffect, useState } from "react"
import { Loader2, Plus, Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"
import { skillsApi } from "@/features/skills/api"
import { SkillEditor } from "@/features/skills/SkillEditor"
import type { Skill } from "@/features/skills/types"
import type { Agent } from "./types"

interface Props {
  agent: Agent
  draft: Agent
  onChange: (patch: Partial<Agent>) => void
}

export function SkillsTab({ agent, draft, onChange }: Props) {
  const { t } = useTranslation("skills")
  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(true)
  const [editor, setEditor] = useState<Skill | "new" | null>(null)

  async function reload() {
    setLoading(true)
    try { setSkills(await skillsApi.list({ agentId: agent.id })) }
    catch { setSkills([]) }
    finally { setLoading(false) }
  }

  useEffect(() => { reload() }, [agent.id])

  const disabled = new Set(draft.disabled_skills ?? [])

  function toggle(name: string) {
    const next = new Set(disabled)
    if (next.has(name)) next.delete(name); else next.add(name)
    onChange({ disabled_skills: Array.from(next) })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 size={20} className="animate-spin text-zinc-500" />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-zinc-500">{t("agent_tab_subtitle", { count: skills.length })}</p>
        <button onClick={() => setEditor("new")}
          className="flex items-center gap-1 px-3 py-1 rounded-md bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-medium">
          <Plus size={11} /> {t("new")}
        </button>
      </div>

      {skills.length === 0 ? (
        <p className="text-xs text-zinc-600 py-6 text-center">{t("agent_tab_empty")}</p>
      ) : (
        <div className="space-y-1">
          {skills.map((s) => {
            const off = disabled.has(s.name)
            return (
              <div key={`${s.scope}:${s.name}`}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg border bg-white/[2%] ${
                  off ? "border-zinc-700/40 opacity-50" : "border-white/[8%]"
                }`}>
                <Sparkles size={12} className="text-violet-300 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-mono text-zinc-200 truncate">{s.name}</p>
                    <span className="text-[10px] text-zinc-600 flex-shrink-0">[{s.scope}]</span>
                  </div>
                  {s.description && <p className="text-[11px] text-zinc-500 truncate">{s.description}</p>}
                </div>
                <button onClick={() => setEditor(s)}
                  className="text-[11px] text-zinc-500 hover:text-zinc-200 px-2 py-0.5 rounded hover:bg-white/5">
                  {t("agent_tab_edit")}
                </button>
                <label className="flex items-center gap-1.5 text-[11px] text-zinc-400 cursor-pointer">
                  <input type="checkbox" checked={!off} onChange={() => toggle(s.name)}
                    className="accent-violet-500" />
                  {off ? t("agent_tab_off") : t("agent_tab_on")}
                </label>
              </div>
            )
          })}
        </div>
      )}

      {editor && (
        <SkillEditor
          skill={editor === "new" ? null : editor}
          defaultScope="agent"
          ownerForSave={agent.id}
          onClose={() => setEditor(null)}
          onSaved={async () => { setEditor(null); await reload() }}
          onDeleted={async () => { setEditor(null); await reload() }}
        />
      )}
    </div>
  )
}
