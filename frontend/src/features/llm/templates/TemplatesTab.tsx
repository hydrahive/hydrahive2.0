import { useCallback, useEffect, useState } from "react"
import { Plus } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { llmModelsApi, type RegistryModel } from "@/features/llm/api"
import { templatesApi } from "./api"
import { TemplateDetail } from "./TemplateDetail"
import { TemplateList } from "./TemplateList"
import { isValidId, newTemplate } from "./templateLogic"
import type { AgentTemplate } from "./types"

/** Reiter „Agenten-Templates“ der LLM-Seite (Spec docs/specs/agent-templates.md Kap. 10). */
export function TemplatesTab() {
  const { t } = useTranslation("llm")
  const isAdmin = useAuthStore((s) => s.role) === "admin"
  const [templates, setTemplates] = useState<AgentTemplate[]>([])
  const [models, setModels] = useState<RegistryModel[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [draft, setDraft] = useState<AgentTemplate | undefined>(undefined)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async (keep?: string) => {
    try {
      const r = await templatesApi.list()
      setTemplates(r.templates)
      setSelected((cur) => keep ?? cur ?? r.templates[0]?.id ?? null)
    } catch (e) { setError(e instanceof Error ? e.message : String(e)) }
  }, [])

  useEffect(() => {
    reload()
    llmModelsApi.byModality("chat").then((r) => setModels(r.models)).catch(() => setModels([]))
  }, [reload])

  function addTemplate() {
    const id = (window.prompt(t("templates.new_prompt")) ?? "").trim()
    if (!id) return
    if (!isValidId(id) || templates.some((x) => x.id === id)) { setError(t("templates.new_invalid")); return }
    const base = templates.find((x) => x.id === selected)
    setDraft(newTemplate(id, base)); setSelected(id); setError(null)
  }

  return (
    <div className="grid gap-4 md:grid-cols-[220px_1fr]">
      <div className="space-y-3">
        <TemplateList templates={templates} selected={selected} onSelect={(id) => { setDraft(undefined); setSelected(id) }} />
        {isAdmin && (
          <button type="button" onClick={addTemplate}
            className="flex w-full items-center justify-center gap-1.5 rounded-[4px] border border-white/[8%] px-2 py-1.5 text-xs text-[#9aa7bc] hover:bg-white/5">
            <Plus size={13} /> {t("templates.new")}
          </button>
        )}
        <p className="px-1 text-[11px] leading-snug text-zinc-500">{t("templates.legend")}</p>
      </div>
      <div className="min-w-0">
        {error && <p role="alert" className="mb-3 text-sm text-rose-400">{error}</p>}
        {selected
          ? <TemplateDetail key={selected + (draft ? ":new" : "")} id={selected} draft={draft} models={models}
              isAdmin={isAdmin} onSaved={(id) => { setDraft(undefined); reload(id) }} />
          : <p className="text-sm text-[#9aa7bc]">{t("templates.empty")}</p>}
      </div>
    </div>
  )
}
