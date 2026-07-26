import {
  ArrowLeft, BrainCircuit, Check, Database, Loader2, Mail, Save,
  SlidersHorizontal, Sparkles, UserRound, Wrench,
} from "lucide-react"
import { useCallback, useEffect, useMemo, useState, type ComponentType } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"
import { mcpInfoApi, type McpServerBrief } from "@/features/agents/api"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { llmModelsApi } from "@/features/llm/api"
import { buddyApi, type BuddyConfig, type BuddyConfigPatch } from "./api"
import { BuddySettingsAdvanced } from "./_BuddySettingsAdvanced"
import { BuddySettingsContext } from "./_BuddySettingsContext"
import { BuddySettingsIdentity } from "./_BuddySettingsIdentity"
import { BuddySettingsMail } from "./_BuddySettingsMail"
import { BuddySettingsModel } from "./_BuddySettingsModel"
import { BuddySettingsSkills } from "./_BuddySettingsSkills"
import { BuddySettingsTools } from "./_BuddySettingsTools"

type TabId = "identity" | "context" | "model" | "tools" | "skills" | "mail" | "advanced"
interface Tab { id: TabId; icon: ComponentType<{ size?: number }>; label: string; show?: boolean }

export function BuddySettingsPage() {
  const { t } = useTranslation("buddy")
  const navigate = useNavigate()
  const [config, setConfig] = useState<BuddyConfig | null>(null)
  const [draft, setDraft] = useState<BuddyConfigPatch>({})
  const [models, setModels] = useState<string[]>([])
  const [mcpServers, setMcpServers] = useState<McpServerBrief[]>([])
  const [activeTab, setActiveTab] = useState<TabId>("identity")
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    const [configResult, modelResult, mcpResult] = await Promise.allSettled([
      buddyApi.getConfig(), llmModelsApi.byModality("chat"), mcpInfoApi.list(),
    ])
    if (configResult.status === "fulfilled") setConfig(configResult.value)
    else setError(configResult.reason instanceof Error ? configResult.reason.message : t("settings.load_error"))
    if (modelResult.status === "fulfilled") setModels(modelResult.value.models.map((model) => model.id))
    if (mcpResult.status === "fulfilled") setMcpServers(mcpResult.value)
    setLoading(false)
  }, [t])

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timer)
  }, [load])

  function applyDraft(patch: BuddyConfigPatch) {
    setDraft((previous) => ({ ...previous, ...patch }))
    setSaved(false)
  }

  async function save() {
    if (!config || Object.keys(draft).length === 0) return
    setBusy(true); setError(null)
    try {
      const result = await buddyApi.patchConfig(draft)
      setConfig(await buddyApi.getConfig())
      setDraft({}); setSaved(true)
      if (result.new_session_id) window.setTimeout(() => navigate("/buddy"), 1200)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t("settings.save_error"))
    } finally { setBusy(false) }
  }

  async function rerollCharacter() {
    setBusy(true); setError(null)
    try {
      await buddyApi.character()
      setConfig(await buddyApi.getConfig())
      setDraft({}); setSaved(true)
      window.setTimeout(() => navigate("/buddy"), 800)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t("settings.save_error"))
    } finally { setBusy(false) }
  }

  const effectiveTools = draft.tools ?? config?.tools ?? []
  const hasMail = effectiveTools.some((tool) => tool === "send_mail" || tool === "read_mail")
  const tabs = useMemo<Tab[]>(() => {
    const all: Tab[] = [
      { id: "identity", icon: UserRound, label: t("settings.tab_identity") },
      { id: "context", icon: Database, label: t("settings.tab_context") },
      { id: "model", icon: BrainCircuit, label: t("settings.tab_model") },
      { id: "tools", icon: Wrench, label: t("settings.tab_tools") },
      { id: "skills", icon: Sparkles, label: t("settings.tab_skills") },
      { id: "mail", icon: Mail, label: t("settings.tab_mail"), show: hasMail },
      { id: "advanced", icon: SlidersHorizontal, label: t("settings.tab_advanced") },
    ]
    return all.filter((tab) => tab.show !== false)
  }, [hasMail, t])

  const visibleTab = tabs.some((tab) => tab.id === activeTab) ? activeTab : "tools"
  const dirty = Object.keys(draft).length > 0

  return <CockpitShell title={t("settings.title")} className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]" hideHeader>
    <CockpitTopbar active="buddy" context={config?.name ?? t("settings.title")} />
    <main className="min-h-0 flex-1 overflow-y-auto p-[10px]">
      <div className="mx-auto flex min-h-full max-w-7xl flex-col gap-4">
        <header className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <button type="button" onClick={() => navigate("/buddy")} aria-label={t("settings.back")} className="mt-0.5 rounded-[4px] border border-[#2a364b] bg-[#151c2b] p-2 text-[#8d9ab0] hover:border-[#46617f] hover:text-[#e8eef8]"><ArrowLeft size={16} /></button>
            <div><h1 className="text-xl font-black text-[#e8eef8]">{t("settings.title")}</h1><p className="mt-1 text-sm text-[#8d9ab0]">{t("settings.subtitle")}</p></div>
          </div>
          {config && <span className="rounded-[4px] border border-[#2a364b] bg-[#151c2b] px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-[#69d7ff]">{config.character || "Buddy"}</span>}
        </header>

        {error && <div className="flex items-center justify-between gap-3 rounded-[4px] border border-rose-400/25 bg-rose-500/10 p-3 text-xs text-rose-200" role="alert"><span>{error}</span>{!config && <button type="button" onClick={() => void load()} className="font-bold underline">{t("settings.retry")}</button>}</div>}

        {loading && !config ? <div className="flex flex-1 items-center justify-center py-24"><Loader2 size={22} className="animate-spin text-[#69d7ff]" /></div> : config && <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[210px_minmax(0,1fr)]">
          <nav className="flex gap-1 overflow-x-auto rounded-[6px] border border-[#2a364b] bg-[#101724] p-2 lg:flex-col lg:self-start" aria-label={t("settings.sections")}>
            {tabs.map(({ id, icon: Icon, label }) => <button key={id} type="button" onClick={() => setActiveTab(id)} className={visibleTab === id ? "flex shrink-0 items-center gap-2 rounded-[4px] border border-[#69d7ff]/40 bg-[#1c2940] px-3 py-2 text-left text-xs font-bold text-[#c8f2ff]" : "flex shrink-0 items-center gap-2 rounded-[4px] border border-transparent px-3 py-2 text-left text-xs font-semibold text-[#8d9ab0] hover:bg-white/5 hover:text-[#e8eef8]"}><Icon size={14} />{label}</button>)}
          </nav>
          <section className="min-w-0 rounded-[6px] border border-[#2a364b] bg-[#101724] p-4 sm:p-5">
            {visibleTab === "identity" && <BuddySettingsIdentity config={config} draft={draft} onChange={applyDraft} onRerollCharacter={() => void rerollCharacter()} busy={busy} />}
            {visibleTab === "context" && <BuddySettingsContext config={config} draft={draft} onChange={applyDraft} />}
            {visibleTab === "model" && <BuddySettingsModel config={config} draft={draft} onChange={applyDraft} availableModels={models} />}
            {visibleTab === "tools" && <BuddySettingsTools config={config} draft={draft} onChange={applyDraft} mcpServers={mcpServers} />}
            {visibleTab === "skills" && <BuddySettingsSkills config={config} draft={draft} onChange={applyDraft} />}
            {visibleTab === "mail" && hasMail && <BuddySettingsMail config={config} draft={draft} onChange={applyDraft} />}
            {visibleTab === "advanced" && <BuddySettingsAdvanced config={config} draft={draft} onChange={applyDraft} availableModels={models} />}
          </section>
        </div>}

        {config && <footer className="sticky bottom-0 flex items-center justify-end gap-3 rounded-[6px] border border-[#2a364b] bg-[#101724]/95 px-4 py-3 backdrop-blur">
          {saved && <span className="flex items-center gap-1.5 text-xs text-emerald-300"><Check size={13} />{t("saved")}</span>}
          {dirty && <button type="button" onClick={() => setDraft({})} disabled={busy} className="rounded-[4px] px-3 py-2 text-xs font-bold text-[#8d9ab0] hover:bg-white/5 hover:text-[#e8eef8]">{t("cancel")}</button>}
          <button type="button" onClick={() => void save()} disabled={!dirty || busy} className="flex items-center gap-1.5 rounded-[4px] border border-[#69d7ff]/45 bg-[#163248] px-4 py-2 text-xs font-bold text-[#c8f2ff] hover:bg-[#1b3d56] disabled:cursor-not-allowed disabled:opacity-40">{busy ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}{t("save")}</button>
        </footer>}
      </div>
    </main>
  </CockpitShell>
}
