import { useEffect, useMemo, useState } from "react"
import { Check, RefreshCw } from "lucide-react"
import { useTranslation } from "react-i18next"
import { agentsApi } from "@/features/agents/api"
import { useAuthStore } from "@/features/auth/useAuthStore"
import type { AgentBrief } from "@/features/chat/types"
import { TemplateSelect } from "@/features/llm/templates/TemplateSelect"
import { CockpitButton } from "../CockpitButton"

interface Props { agentId: string | null; agents: AgentBrief[]; onAgentChanged: (agent: AgentBrief) => void }

/** KI-Einstellungen des Projekt-Agenten: nur noch das Agenten-Template (docs/specs/agent-templates.md).
 *  Modell, Failover und Budget stellt der Admin am Template ein (LLM-Seite). */
export function ProjectAiSettingsPanel({ agentId, agents, onAgentChanged }: Props) {
  const { t } = useTranslation("agents")
  const isAdmin = useAuthStore((s) => s.role) === "admin"
  const agent = useMemo(() => agents.find((item) => item.id === agentId) ?? null, [agents, agentId])
  const [template, setTemplate] = useState("")
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => { setTemplate(agent?.template ?? ""); setMessage(null); setError(null) }, [agent?.id, agent?.template])

  if (!agent) return <p className="text-xs text-[#9aa7bc]">Kein Projekt-Agent ausgewählt.</p>
  const dirty = template !== (agent.template ?? "") && !!template

  async function save() {
    if (!agent || !dirty) return
    setSaving(true); setMessage(null); setError(null)
    try {
      const updated = await agentsApi.update(agent.id, { template })
      onAgentChanged({ ...agent, template: updated.template, llm_model: updated.llm_model })
      setMessage(t("template.saved"))
    } catch (e) { setError(e instanceof Error ? e.message : t("template.save_failed")) }
    finally { setSaving(false) }
  }

  return <div className="space-y-3" data-template-panel>
    <div>
      <label htmlFor="project-ai-template" className="mb-1 block text-xs text-[#9aa7bc]">{t("template.label")}</label>
      <TemplateSelect id="project-ai-template" value={template} onChange={setTemplate} groups={["projects", "specialists"]}
        className="w-full rounded-[4px] border border-s-rand bg-s-tief px-3 py-2 text-sm font-semibold text-[#e8eef8] outline-none hover:border-s-rand-hover disabled:opacity-50" />
      <p className="mt-1 text-[11px] text-[#9aa7bc]">{t("template.managed_hint")}</p>
    </div>
    {error && <p className="text-xs text-rose-300">{error}</p>}{message && <p className="text-xs text-emerald-300">{message}</p>}
    {isAdmin && <div className="flex gap-2">
      <CockpitButton tone="primary" disabled={!dirty || saving} onClick={() => void save()}>
        {saving ? <RefreshCw size={12} className="mr-1 inline animate-spin" /> : <Check size={12} className="mr-1 inline" />}{t("template.save")}
      </CockpitButton>
      <CockpitButton disabled={!dirty || saving} onClick={() => setTemplate(agent.template ?? "")}>{t("template.reset")}</CockpitButton>
    </div>}
  </div>
}
