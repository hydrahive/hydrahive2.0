import { useState } from "react"
import { Loader2, Plus, Save, Trash2, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { skillsApi } from "./api"
import type { Skill, SkillScope, SkillSource } from "./types"

interface Props {
  skill: Skill | null  // null = neu
  defaultScope?: SkillScope
  ownerForSave?: string  // bei agent-scope = agent_id
  onClose: () => void
  onSaved: () => void
  onDeleted?: () => void
}

const NAME_RE = /^[a-z0-9][a-z0-9_-]{0,49}$/

export function SkillEditor({ skill, defaultScope = "user", ownerForSave, onClose, onSaved, onDeleted }: Props) {
  const { t } = useTranslation("skills")
  const { t: tCommon } = useTranslation("common")
  const isNew = !skill
  const [name, setName] = useState(skill?.name ?? "")
  const [description, setDescription] = useState(skill?.description ?? "")
  const [whenToUse, setWhenToUse] = useState(skill?.when_to_use ?? "")
  const [toolsRequired, setToolsRequired] = useState((skill?.tools_required ?? []).join(", "))
  const [sources, setSources] = useState<SkillSource[]>(skill?.sources ?? [])
  const [body, setBody] = useState(skill?.body ?? "")
  const [scope] = useState<SkillScope>(skill?.scope ?? defaultScope)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const validName = NAME_RE.test(name)

  async function save() {
    if (!validName) { setError(t("name_invalid")); return }
    setBusy(true); setError(null)
    try {
      const tools = toolsRequired.split(",").map((s) => s.trim()).filter(Boolean)
      const owner = scope === "agent" ? ownerForSave : skill?.owner
      await skillsApi.save(scope, {
        name, description, when_to_use: whenToUse,
        tools_required: tools,
        sources: sources.filter((s) => s.url.trim()),
        body,
      }, owner)
      onSaved()
    } catch (e) {
      setError(e instanceof Error ? e.message : tCommon("status.error"))
    } finally { setBusy(false) }
  }

  async function remove() {
    if (!skill) return
    if (!confirm(t("delete_confirm", { name: skill.name }))) return
    setBusy(true); setError(null)
    try {
      await skillsApi.remove(skill.scope, skill.name, skill.owner)
      onDeleted?.()
    } catch (e) {
      setError(e instanceof Error ? e.message : tCommon("status.error"))
    } finally { setBusy(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()}
        className="w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-2xl border border-white/[8%] bg-zinc-900 p-5 shadow-2xl shadow-black/40 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">
            {isNew ? t("new_title") : t("edit_title", { name: skill!.name })}
            <span className="ml-2 text-[10px] text-zinc-500 font-normal">[{scope}]</span>
          </h2>
          <button onClick={onClose} className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
            <X size={16} />
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <Field label={t("name")}>
            <input value={name} onChange={(e) => setName(e.target.value)} disabled={!isNew}
              placeholder="code-review"
              className={`w-full px-2 py-1 rounded-md bg-zinc-950 border text-xs text-zinc-200 font-mono ${
                name && !validName ? "border-rose-500/40" : "border-white/[8%]"
              } disabled:opacity-50`} />
            {!isNew && <p className="text-[10px] text-zinc-600 mt-0.5">{t("name_immutable")}</p>}
          </Field>
          <Field label={t("tools_required")}>
            <input value={toolsRequired} onChange={(e) => setToolsRequired(e.target.value)}
              placeholder="file_read, shell_exec"
              className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 font-mono" />
          </Field>
        </div>

        <Field label={t("description")}>
          <input value={description} onChange={(e) => setDescription(e.target.value)}
            placeholder={t("description_placeholder")}
            className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200" />
        </Field>

        <Field label={t("when_to_use")} hint={t("when_to_use_hint")}>
          <input value={whenToUse} onChange={(e) => setWhenToUse(e.target.value)}
            placeholder={t("when_to_use_placeholder")}
            className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200" />
        </Field>

        <Field label={t("sources")} hint={t("sources_hint")}>
          <div className="space-y-1">
            {sources.map((src, i) => (
              <div key={i} className="grid grid-cols-[1fr_auto_auto] gap-1 items-start">
                <div className="space-y-0.5">
                  <input value={src.url}
                    onChange={(e) => setSources(sources.map((s, j) => j === i ? { ...s, url: e.target.value } : s))}
                    placeholder="https://forum.metin2.de/api/threads"
                    className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 font-mono" />
                  <input value={src.description}
                    onChange={(e) => setSources(sources.map((s, j) => j === i ? { ...s, description: e.target.value } : s))}
                    placeholder={t("source_description_placeholder")}
                    className="w-full px-2 py-1 rounded-md bg-zinc-950/50 border border-white/[6%] text-[11px] text-zinc-400" />
                </div>
                <input value={src.auth}
                  onChange={(e) => setSources(sources.map((s, j) => j === i ? { ...s, auth: e.target.value } : s))}
                  placeholder={t("source_auth_placeholder")}
                  title={t("source_auth_hint")}
                  className="w-32 px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 font-mono self-start" />
                <button type="button"
                  onClick={() => setSources(sources.filter((_, j) => j !== i))}
                  className="p-1.5 rounded text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 self-start">
                  <Trash2 size={11} />
                </button>
              </div>
            ))}
            <button type="button"
              onClick={() => setSources([...sources, { url: "", auth: "", description: "" }])}
              className="flex items-center gap-1 px-2 py-1 rounded-md text-[11px] text-zinc-400 hover:text-zinc-200 hover:bg-white/5 border border-white/[8%] border-dashed">
              <Plus size={11} /> {t("source_add")}
            </button>
          </div>
        </Field>

        <Field label={t("body")}>
          <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={14}
            placeholder={t("body_placeholder")}
            className="w-full px-2 py-1.5 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 font-mono leading-relaxed focus:outline-none focus:ring-1 focus:ring-violet-500/50" />
        </Field>

        {error && (
          <p className="text-xs text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-lg px-3 py-2">{error}</p>
        )}

        <div className="flex justify-between gap-2 pt-1">
          {!isNew && onDeleted && skill?.scope !== "system" && (
            <button onClick={remove} disabled={busy}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs text-rose-300 hover:bg-rose-500/10 border border-rose-500/30 disabled:opacity-30">
              <Trash2 size={11} /> {tCommon("actions.delete")}
            </button>
          )}
          <div className="flex-1" />
          <button onClick={onClose}
            className="px-3 py-1.5 rounded-md text-xs text-zinc-400 hover:text-zinc-200 hover:bg-white/5">
            {tCommon("actions.cancel")}
          </button>
          <button onClick={save} disabled={!validName || busy}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-medium disabled:opacity-30">
            {busy ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
            {tCommon("actions.save")}
          </button>
        </div>
      </div>
    </div>
  )
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-0.5">
      <label className="block text-[10px] font-medium text-zinc-500">{label}</label>
      {children}
      {hint && <p className="text-[10px] text-zinc-600 mt-0.5">{hint}</p>}
    </div>
  )
}
