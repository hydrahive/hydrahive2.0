import { useState } from "react"
import { Eye, EyeOff, Loader2, Save } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import type { Project } from "./types"

interface Props { project: Project; onSaved: (p: Project) => void }

export function OverridesSection({ project, onSaved }: Props) {
  const { t } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const [mcpIds, setMcpIds] = useState((project.mcp_server_ids ?? []).join(", "))
  const [plugins, setPlugins] = useState((project.allowed_plugins ?? []).join(", "))
  const [apiKey, setApiKey] = useState(project.llm_api_key ?? "")
  const [showKey, setShowKey] = useState(false)
  const [saving, setSaving] = useState(false)

  async function save() {
    setSaving(true)
    try {
      const updated = await projectsApi.update(project.id, {
        mcp_server_ids: mcpIds.split(",").map(s => s.trim()).filter(Boolean),
        allowed_plugins: plugins.split(",").map(s => s.trim()).filter(Boolean),
        llm_api_key: apiKey.trim(),
      })
      onSaved(updated)
    } finally { setSaving(false) }
  }

  return (
    <div className="space-y-4 pt-4 border-t border-white/[6%]">
      <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">{t("overrides.title")}</p>
      {[
        { label: t("overrides.mcp_label"), hint: t("overrides.mcp_hint"), value: mcpIds, onChange: setMcpIds },
        { label: t("overrides.plugins_label"), hint: t("overrides.plugins_hint"), value: plugins, onChange: setPlugins },
      ].map(({ label, hint, value, onChange }) => (
        <div key={label} className="space-y-1">
          <label className="block text-xs font-medium text-zinc-500">{label}</label>
          <input value={value} onChange={e => onChange(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-white/[8%] text-xs text-zinc-300 font-mono" />
          <p className="text-[10px] text-zinc-600">{hint}</p>
        </div>
      ))}
      <div className="space-y-1">
        <label className="block text-xs font-medium text-zinc-500">{t("overrides.api_key_label")}</label>
        <div className="flex gap-2">
          <input type={showKey ? "text" : "password"} value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            className="flex-1 px-3 py-2 rounded-lg bg-zinc-900 border border-white/[8%] text-xs text-zinc-300 font-mono" />
          <button onClick={() => setShowKey(s => !s)} className="px-2 text-zinc-500 hover:text-zinc-200">
            {showKey ? <EyeOff size={13} /> : <Eye size={13} />}
          </button>
        </div>
        <p className="text-[10px] text-zinc-600">{t("overrides.api_key_hint")}</p>
      </div>
      <button onClick={save} disabled={saving}
        className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-30 transition-all">
        {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
        {tCommon("actions.save")}
      </button>
    </div>
  )
}
