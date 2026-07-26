import { useCallback, useEffect, useMemo, useState } from "react"
import { Loader2, Pencil, Plus, RefreshCw, Search, Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"
import { SkillEditor } from "@/features/skills/SkillEditor"
import { skillsApi } from "@/features/skills/api"
import type { Skill, SkillScope } from "@/features/skills/types"
import type { BuddyConfig, BuddyConfigPatch } from "./api"

interface Props {
  config: BuddyConfig
  draft: BuddyConfigPatch
  onChange: (patch: BuddyConfigPatch) => void
}

export function BuddySettingsSkills({ config, draft, onChange }: Props) {
  const { t } = useTranslation("buddy")
  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState("")
  const [editor, setEditor] = useState<Skill | "new" | null>(null)
  const disabled = draft.disabled_skills ?? config.disabled_skills

  const reload = useCallback(async () => {
    setLoading(true); setError(null)
    try { setSkills(await skillsApi.list({ agentId: config.agent_id, includeDisabled: true })) }
    catch (error) { setError(error instanceof Error ? error.message : t("skills.load_error")) }
    finally { setLoading(false) }
  }, [config.agent_id, t])

  useEffect(() => { void reload() }, [reload])

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return skills.filter((skill) => !needle || `${skill.name} ${skill.description} ${skill.when_to_use} ${skill.scope}`.toLowerCase().includes(needle))
  }, [query, skills])
  const counts = skills.reduce<Record<string, number>>((acc, skill) => ({ ...acc, [skill.scope]: (acc[skill.scope] ?? 0) + 1 }), {})

  function toggle(name: string) {
    onChange({ disabled_skills: disabled.includes(name) ? disabled.filter((item) => item !== name) : [...disabled, name] })
  }

  async function afterDelete(name: string) {
    if (disabled.includes(name)) onChange({ disabled_skills: disabled.filter((item) => item !== name) })
    setEditor(null)
    await reload()
  }

  return <div className="space-y-4">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div className="flex flex-wrap gap-1.5">
        {(["system", "user", "project", "agent"] as SkillScope[]).map((scope) => <span key={scope} className="rounded-[4px] border border-[#2a364b] bg-[#111827] px-2 py-1 text-[10px] font-semibold text-[#8d9ab0]">{t(`skills.scope_${scope}`)} · {counts[scope] ?? 0}</span>)}
      </div>
      <button type="button" onClick={() => setEditor("new")} className="flex items-center gap-1.5 rounded-[4px] border border-[#69d7ff]/45 bg-[#163248] px-3 py-1.5 text-xs font-bold text-[#c8f2ff] hover:bg-[#1b3d56]"><Plus size={13} />{t("skills.new")}</button>
    </div>
    <label className="flex items-center gap-2 rounded-[4px] border border-[#2a364b] bg-[#0b111c] px-3 py-2"><Search size={14} className="text-[#718097]" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("skills.search")} className="min-w-0 flex-1 bg-transparent text-sm text-[#e8eef8] outline-none placeholder:text-[#59677d]" /></label>

    {loading ? <div className="flex justify-center py-16"><Loader2 size={20} className="animate-spin text-[#69d7ff]" /></div> : error ? <div className="rounded-[4px] border border-rose-400/25 bg-rose-500/10 p-4 text-sm text-rose-200"><p>{error}</p><button type="button" onClick={() => void reload()} className="mt-3 flex items-center gap-1.5 text-xs font-bold"><RefreshCw size={13} />{t("settings.retry")}</button></div> : <div className="grid max-h-[58vh] gap-2 overflow-y-auto pr-1 md:grid-cols-2">
      {filtered.map((skill) => {
        const enabled = !disabled.includes(skill.name)
        const editable = skill.scope === "agent" && skill.owner === config.agent_id
        return <article key={`${skill.scope}:${skill.owner}:${skill.name}`} className={`rounded-[4px] border p-3 ${enabled ? "border-[#2a364b] bg-[#111827]" : "border-[#2a364b] bg-[#0b111c] opacity-70"}`}>
          <div className="flex items-start gap-2"><Sparkles size={14} className="mt-0.5 shrink-0 text-[#69d7ff]" /><div className="min-w-0 flex-1"><div className="flex items-center gap-2"><h3 className="truncate font-mono text-sm font-semibold text-[#e8eef8]">{skill.name}</h3><span className="rounded-[3px] border border-[#2a364b] px-1.5 py-0.5 text-[9px] uppercase text-[#8d9ab0]">{t(`skills.scope_${skill.scope}`)}</span></div>{skill.description && <p className="mt-1 line-clamp-2 text-xs leading-4 text-[#8d9ab0]">{skill.description}</p>}</div>{editable && <button type="button" onClick={() => setEditor(skill)} title={t("skills.edit")} className="rounded p-1.5 text-[#8d9ab0] hover:bg-white/5 hover:text-[#e8eef8]"><Pencil size={13} /></button>}</div>
          <label className="mt-3 flex cursor-pointer items-center justify-between border-t border-[#2a364b] pt-2 text-xs text-[#8d9ab0]"><span>{enabled ? t("skills.enabled") : t("skills.disabled")}</span><input type="checkbox" checked={enabled} onChange={() => toggle(skill.name)} className="accent-[#69d7ff]" /></label>
        </article>
      })}
      {filtered.length === 0 && <p className="py-10 text-center text-sm text-[#718097] md:col-span-2">{t("skills.empty")}</p>}
    </div>}

    {editor && <SkillEditor skill={editor === "new" ? null : editor} defaultScope="agent" ownerForSave={config.agent_id} onClose={() => setEditor(null)} onSaved={async () => { setEditor(null); await reload() }} onDeleted={editor === "new" ? undefined : async () => afterDelete(editor.name)} />}
  </div>
}
