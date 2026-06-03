import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { ArrowLeft, Check, Loader2 } from "lucide-react"
import { useNavigate } from "react-router-dom"
import { buddyApi, type BuddyConfig, type BuddyConfigPatch } from "./api"
import { llmInfoApi } from "@/features/agents/api"
import { BuddySettingsIdentity } from "./_BuddySettingsIdentity"
import { BuddySettingsContext } from "./_BuddySettingsContext"
import { BuddySettingsTools } from "./_BuddySettingsTools"
import { BuddySettingsMail } from "./_BuddySettingsMail"
import { BuddySettingsCompaction } from "./_BuddySettingsCompaction"

type TabId = "identity" | "context" | "tools" | "mail" | "compaction"

export function BuddySettingsPage() {
  const { t } = useTranslation("buddy")
  const navigate = useNavigate()
  const [config, setConfig] = useState<BuddyConfig | null>(null)
  const [draft, setDraft] = useState<BuddyConfigPatch>({})
  const [models, setModels] = useState<string[]>([])
  const [activeTab, setActiveTab] = useState<TabId>("identity")
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const hasMail = !!config?.tools?.some((tool) => tool === "send_mail" || tool === "read_mail")
  const TABS: { id: TabId; label: string }[] = [
    { id: "identity", label: t("settings.tab_identity") },
    { id: "context", label: t("settings.tab_context") },
    { id: "tools", label: t("settings.tab_tools") },
    ...(hasMail ? [{ id: "mail" as const, label: t("settings.tab_mail") }] : []),
    { id: "compaction", label: t("settings.tab_compaction") },
  ]

  useEffect(() => {
    buddyApi.getConfig().then(setConfig).catch((e: unknown) =>
      setError(e instanceof Error ? e.message : t("settings.title")))
    llmInfoApi.getModels().then((r) => setModels(r.models)).catch(() => {})
  }, [])

  function applyDraft(patch: BuddyConfigPatch) {
    setDraft((prev) => ({ ...prev, ...patch }))
    setSaved(false)
  }

  async function save() {
    if (!config || Object.keys(draft).length === 0) return
    setBusy(true); setError(null)
    try {
      const result = await buddyApi.patchConfig(draft)
      const fresh = await buddyApi.getConfig()
      setConfig(fresh)
      setDraft({})
      setSaved(true)
      if (result.new_session_id) {
        setTimeout(() => navigate("/"), 1200)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : t("settings.title"))
    } finally {
      setBusy(false)
    }
  }

  async function handleReroll() {
    if (!config) return
    setBusy(true)
    try {
      await buddyApi.character()
      const fresh = await buddyApi.getConfig()
      setConfig(fresh)
      setTimeout(() => navigate("/"), 800)
    } finally {
      setBusy(false)
    }
  }

  const hasDraft = Object.keys(draft).length > 0

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate("/")}
          className="p-2 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-white/5 transition-all"
        >
          <ArrowLeft size={16} />
        </button>
        <div className="flex items-center gap-2">
          <span className="text-2xl">🐝</span>
          <h1 className="text-lg font-bold text-white">{t("settings.title")}</h1>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-500/20 bg-rose-500/[4%] px-4 py-3 text-sm text-rose-300">
          {error}
        </div>
      )}

      {!config ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={20} className="text-zinc-500 animate-spin" />
        </div>
      ) : (
        <>
          <div className="rounded-2xl border border-white/[8%] bg-zinc-900/80 overflow-hidden">
            <div className="flex border-b border-white/[6%]">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 px-4 py-3 text-xs font-medium transition-all ${
                    activeTab === tab.id
                      ? "text-white bg-white/[4%] border-b-2 border-violet-500"
                      : "text-zinc-500 hover:text-zinc-300 hover:bg-white/[2%]"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="p-6">
              {activeTab === "identity" && (
                <BuddySettingsIdentity
                  config={config}
                  draft={draft}
                  onChange={applyDraft}
                  onRerollCharacter={handleReroll}
                  busy={busy}
                />
              )}
              {activeTab === "context" && (
                <BuddySettingsContext config={config} draft={draft} onChange={applyDraft} />
              )}
              {activeTab === "tools" && (
                <BuddySettingsTools config={config} draft={draft} onChange={applyDraft} />
              )}
              {activeTab === "mail" && hasMail && (
                <BuddySettingsMail config={config} draft={draft} onChange={applyDraft} />
              )}
              {activeTab === "compaction" && (
                <BuddySettingsCompaction
                  config={config}
                  draft={draft}
                  onChange={applyDraft}
                  availableModels={models}
                />
              )}
            </div>
          </div>

          <div className="flex items-center justify-end gap-3">
            {saved && (
              <div className="flex items-center gap-1.5 text-xs text-emerald-400">
                <Check size={13} />
                {t("saved")}
              </div>
            )}
            <button
              onClick={() => navigate("/")}
              className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/5"
            >
              {t("cancel")}
            </button>
            <button
              onClick={save}
              disabled={!hasDraft || busy}
              className="px-5 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed shadow-md shadow-violet-900/20 transition-all"
            >
              {busy ? <Loader2 size={14} className="animate-spin" /> : t("save")}
            </button>
          </div>
        </>
      )}
    </div>
  )
}
