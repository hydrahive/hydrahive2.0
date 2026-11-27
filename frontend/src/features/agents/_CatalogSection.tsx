import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { skillsApi } from "@/features/skills/api"
import type { Skill } from "@/features/skills/types"
import { toolPoolApi, type AgentToolPool } from "./api"
import { ToolsSelector } from "./ToolsSelector"
import { pinnable } from "./_pinnable"
import type { Agent, ToolMeta } from "./types"

interface Props {
  draft: Agent
  tools: ToolMeta[]
  onChange: (patch: Partial<Agent>) => void
}

const box = "rounded-md border border-white/[8%] bg-white/[2%] px-3 py-2.5 space-y-2"

/**
 * Expertenansicht des Katalog-Modus: angeheftete Tools/Skills und Freigabe-Pool (Spec tool-skill-katalog, Auftrag 6b).
 * Den Modus selbst schaltet der Bereichs-Schalter „Werkzeuge bei Bedarf suchen“ (areas/AreasView), nicht mehr ein Knopf hier.
 */
export function CatalogSection({ draft, tools, onChange }: Props) {
  const mode = draft.tool_mode ?? "classic"
  return (
    <div className="space-y-4" data-testid="catalog-section">
      {mode === "catalog" && <PinnedSection draft={draft} tools={tools} onChange={onChange} />}
      <PoolSection agent={draft} tools={tools} />
    </div>
  )
}

function PinnedSection({ draft, tools, onChange }: Props) {
  const { t } = useTranslation("agents")
  const [skills, setSkills] = useState<Skill[]>([])
  useEffect(() => { skillsApi.list({ agentId: draft.id }).then(setSkills).catch(() => {}) }, [draft.id])
  const pinnedSkills = new Set(draft.pinned_skills ?? [])
  const names = Array.from(new Set([...skills.map((s) => s.name), ...pinnedSkills]))
  function toggleSkill(name: string) {
    const next = new Set(pinnedSkills)
    if (next.has(name)) next.delete(name)
    else next.add(name)
    onChange({ pinned_skills: Array.from(next) })
  }
  return (
    <div className={box}>
      <p className="text-[10px] font-medium text-zinc-500">{t("catalog.pinned_tools", { count: (draft.pinned_tools ?? []).length })}</p>
      <p className="text-[10px] text-zinc-500">{t("catalog.pinned_tools_hint")}</p>
      <ToolsSelector available={pinnable(draft, tools)} selected={draft.pinned_tools ?? []} onChange={(v) => onChange({ pinned_tools: v })} />
      <p className="text-[10px] font-medium text-zinc-500 pt-1">{t("catalog.pinned_skills", { count: pinnedSkills.size })}</p>
      <div className="flex flex-wrap gap-1">
        {names.length === 0 && <span className="text-[10px] text-zinc-600">{t("catalog.no_skills")}</span>}
        {names.map((name) => (
          <button
            key={name}
            type="button"
            onClick={() => toggleSkill(name)}
            className={`px-2 py-0.5 rounded-md border text-[11px] font-mono ${
              pinnedSkills.has(name) ? "border-violet-500/40 bg-violet-500/[10%] text-zinc-100" : "border-white/[6%] text-zinc-400 hover:bg-white/[4%]"
            }`}
          >
            {name}
          </button>
        ))}
      </div>
    </div>
  )
}

function PoolSection({ agent, tools }: { agent: Agent; tools: ToolMeta[] }) {
  const { t } = useTranslation("agents")
  const { username, role } = useAuthStore()
  const mayEdit = role === "admin" || (!!username && username === agent.owner)
  const [pool, setPool] = useState<AgentToolPool | null>(null)
  const [items, setItems] = useState<string[]>([])
  const [saved, setSaved] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)

  useEffect(() => {
    let alive = true
    toolPoolApi.get(agent.id)
      .then((p) => { if (alive) { setPool(p); setItems(p.items); setSaved(p.items) } })
      .catch((e) => { if (alive) setError(e instanceof Error ? e.message : String(e)) })
    return () => { alive = false }
  }, [agent.id])

  const forbidden = new Set(pool?.forbidden ?? [])
  const offered = tools.filter((tool) => !forbidden.has(tool.name) && !tool.name.startsWith("mcp__"))
  const dirty = JSON.stringify(items) !== JSON.stringify(saved)

  function toggleCategory(cat: string) {
    const entry = `kategorie:${cat}`
    setDone(false)
    setItems((cur) => (cur.includes(entry) ? cur.filter((i) => i !== entry) : [...cur, entry]))
  }

  async function save() {
    setBusy(true); setError(null); setDone(false)
    try {
      const res = await toolPoolApi.put(agent.id, items)
      setItems(res.items); setSaved(res.items); setDone(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : t("catalog.pool_save_failed"))
    } finally { setBusy(false) }
  }

  return (
    <div className={box} data-testid="pool-section">
      <p className="text-xs font-medium text-zinc-200">{t("catalog.pool_title")}</p>
      <p className="text-[10px] text-zinc-500">{mayEdit ? t("catalog.pool_hint") : t("catalog.pool_readonly")}</p>
      {pool && (
        <>
          <div className="flex flex-wrap gap-1">
            {(pool.categories ?? []).map((cat) => {
              const on = items.includes(`kategorie:${cat}`)
              return (
                <button
                  key={cat}
                  type="button"
                  disabled={!mayEdit}
                  onClick={() => toggleCategory(cat)}
                  className={`px-2 py-0.5 rounded-md border text-[11px] font-mono disabled:opacity-60 ${
                    on ? "border-violet-500/40 bg-violet-500/[10%] text-zinc-100" : "border-white/[6%] text-zinc-400 hover:bg-white/[4%]"
                  }`}
                >
                  kategorie:{cat}
                </button>
              )
            })}
          </div>
          {mayEdit ? (
            <ToolsSelector available={offered} selected={items} hideCategoryEntries onChange={(v) => { setDone(false); setItems(v) }} />
          ) : (
            <p className="text-[11px] font-mono text-zinc-300 break-words">{items.join(", ") || t("catalog.pool_empty")}</p>
          )}
        </>
      )}
      {error && <p className="text-[11px] text-red-400" role="alert">{error}</p>}
      {done && <p className="text-[11px] text-emerald-400">{t("catalog.pool_saved")}</p>}
      {mayEdit && (
        <button
          type="button"
          disabled={!dirty || busy}
          onClick={save}
          className="px-3 py-1 rounded-md bg-violet-600 text-xs text-white disabled:opacity-40"
        >
          {t("catalog.pool_save")}
        </button>
      )}
    </div>
  )
}
