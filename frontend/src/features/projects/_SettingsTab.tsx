import { useEffect, useState } from "react"
import { CheckCircle2, Copy, Eye, EyeOff, FolderOpen, Loader2, Save, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import type { Project } from "./types"

interface OverrideProps { project: Project; onSaved: (p: Project) => void }

function OverridesSection({ project, onSaved }: OverrideProps) {
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
          <input
            type={showKey ? "text" : "password"}
            value={apiKey} onChange={e => setApiKey(e.target.value)}
            className="flex-1 px-3 py-2 rounded-lg bg-zinc-900 border border-white/[8%] text-xs text-zinc-300 font-mono"
          />
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

interface Props {
  project: Project
  draft: Project
  onDraftChange: (p: Project) => void
  onDeleted: () => void
}

export function SettingsTab({ project, draft, onDraftChange, onDeleted }: Props) {
  const { t } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const [samba, setSamba] = useState<{ enabled: boolean; share_name: string; user: string; password: string } | null>(null)
  const [sambaBusy, setSambaBusy] = useState(false)
  const [sambaError, setSambaError] = useState<string | null>(null)
  const [copied, setCopied] = useState<"" | "url" | "user" | "password">("")
  const [showPwd, setShowPwd] = useState(false)

  useEffect(() => {
    projectsApi.getSamba(project.id).then(setSamba).catch(() => setSamba(null))
  }, [project.id])

  async function toggleSamba() {
    if (!samba) return
    setSambaBusy(true); setSambaError(null)
    try {
      await projectsApi.putSamba(project.id, !samba.enabled)
      const fresh = await projectsApi.getSamba(project.id)
      setSamba(fresh)
    } catch (e) {
      setSambaError(e instanceof Error ? e.message : tCommon("status.error"))
    } finally { setSambaBusy(false) }
  }

  async function copyText(value: string, key: "url" | "user" | "password") {
    await navigator.clipboard.writeText(value)
    setCopied(key); setTimeout(() => setCopied(""), 1500)
  }

  async function remove() {
    if (!confirm(t("delete_confirm", { name: project.name }))) return
    await projectsApi.delete(project.id)
    onDeleted()
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-zinc-500 uppercase tracking-wider">
          {tCommon("labels.status")}
        </label>
        <select
          value={draft.status}
          onChange={(e) => onDraftChange({ ...draft, status: e.target.value as Project["status"] })}
          className="px-3 py-2 rounded-lg bg-zinc-900 border border-white/[8%] text-sm text-zinc-300 w-full"
        >
          <option value="active">{tCommon("status.active")}</option>
          <option value="paused">{tCommon("status.paused")}</option>
          <option value="archived">{tCommon("status.archived")}</option>
        </select>
      </div>

      {samba && (
        <div className="rounded-lg border border-white/[6%] bg-white/[2%] p-3 space-y-2">
          <div className="flex items-center gap-2">
            <FolderOpen size={14} className="text-amber-300" />
            <p className="text-sm font-medium text-zinc-200 flex-1">{t("samba.title")}</p>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={samba.enabled} disabled={sambaBusy}
                onChange={toggleSamba}
                className="w-4 h-4 accent-amber-500" />
              <span className="text-xs text-zinc-400">{t("samba.enable")}</span>
              {sambaBusy && <Loader2 size={11} className="animate-spin text-amber-400" />}
            </label>
          </div>
          {samba.enabled && (
            <>
              <div className="flex items-center gap-2 pt-1">
                <code className="text-xs text-amber-300 bg-amber-500/[6%] border border-amber-500/20 rounded px-2 py-1 font-mono flex-1 truncate">
                  {`\\\\${window.location.hostname}\\${samba.share_name}`}
                </code>
                <button onClick={() => copyText(`\\\\${window.location.hostname}\\${samba.share_name}`, "url")}
                  className="p-1.5 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5"
                  title={copied === "url" ? t("samba.copied") : t("samba.copy")}>
                  {copied === "url" ? <CheckCircle2 size={12} className="text-emerald-400" /> : <Copy size={12} />}
                </button>
              </div>
              <div className="grid grid-cols-[auto_1fr_auto] gap-x-2 gap-y-1 items-center pt-1">
                <span className="text-[10px] text-zinc-500">{t("samba.user_label")}</span>
                <code className="text-xs text-zinc-300 bg-zinc-900 border border-white/[8%] rounded px-2 py-0.5 font-mono truncate">{samba.user}</code>
                <button onClick={() => copyText(samba.user, "user")}
                  className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
                  {copied === "user" ? <CheckCircle2 size={11} className="text-emerald-400" /> : <Copy size={11} />}
                </button>
                <span className="text-[10px] text-zinc-500">{t("samba.password_label")}</span>
                <code className="text-xs text-zinc-300 bg-zinc-900 border border-white/[8%] rounded px-2 py-0.5 font-mono truncate">
                  {showPwd ? samba.password : "••••••••••••"}
                </code>
                <div className="flex gap-0.5">
                  <button onClick={() => setShowPwd(!showPwd)}
                    className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
                    {showPwd ? <EyeOff size={11} /> : <Eye size={11} />}
                  </button>
                  <button onClick={() => copyText(samba.password, "password")}
                    className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
                    {copied === "password" ? <CheckCircle2 size={11} className="text-emerald-400" /> : <Copy size={11} />}
                  </button>
                </div>
              </div>
            </>
          )}
          <p className="text-[10px] text-zinc-600">{t("samba.hint_inline")}</p>
          {sambaError && (
            <p className="text-xs text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-md px-2 py-1">{sambaError}</p>
          )}
        </div>
      )}

      <OverridesSection project={project} onSaved={onDraftChange} />

      <div className="pt-4 border-t border-white/[6%]">
        <p className="text-xs text-zinc-600 mb-3">{t("settings.danger_zone")}</p>
        <button
          onClick={remove}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-rose-500/30 text-rose-400 hover:bg-rose-500/[8%] transition-colors text-sm"
        >
          <Trash2 size={14} />
          {t("settings.delete_project")}
        </button>
      </div>
    </div>
  )
}
