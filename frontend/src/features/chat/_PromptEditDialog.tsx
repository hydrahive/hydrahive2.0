import { useState } from "react"
import { useTranslation } from "react-i18next"
import { X } from "lucide-react"
import { PROMPT_CATEGORIES, type PromptCategory, type PromptEntry, type PromptInput } from "./promptArchive"

interface Props {
  /** Vorhandener Eintrag = Bearbeiten; undefined = Neu anlegen. */
  entry?: PromptEntry
  onSave: (body: PromptInput) => Promise<void>
  onClose: () => void
}

/** Modal zum Anlegen/Bearbeiten eines Prompt-Rezepts. */
export function PromptEditDialog({ entry, onSave, onClose }: Props) {
  const { t } = useTranslation("chat")
  const [title, setTitle] = useState(entry?.title ?? "")
  const [category, setCategory] = useState<PromptCategory>(entry?.category ?? "image")
  const [prompt, setPrompt] = useState(entry?.prompt ?? "")
  const [styleAnchor, setStyleAnchor] = useState(entry?.style_anchor ?? "")
  const [model, setModel] = useState(entry?.model ?? "")
  const [tags, setTags] = useState((entry?.tags ?? []).join(", "))
  const [notes, setNotes] = useState(entry?.notes ?? "")
  const [isPublic, setIsPublic] = useState(entry?.is_public ?? false)
  const [busy, setBusy] = useState(false)

  async function submit() {
    if (!title.trim() || !prompt.trim() || busy) return
    setBusy(true)
    try {
      await onSave({
        title: title.trim(),
        category,
        prompt: prompt.trim(),
        style_anchor: styleAnchor.trim() || null,
        model: model.trim() || null,
        tags: tags.split(",").map((x) => x.trim()).filter(Boolean),
        notes: notes.trim() || null,
        is_public: isPublic,
      })
      onClose()
    } finally {
      setBusy(false)
    }
  }

  const field = "w-full rounded-lg bg-white/[4%] border border-white/10 px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-violet-500/40"

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onMouseDown={onClose}>
      <div className="w-full max-w-lg rounded-2xl bg-zinc-900 border border-white/10 shadow-2xl max-h-[90vh] overflow-y-auto"
        onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/10">
          <h3 className="text-sm font-semibold text-zinc-200">
            {entry ? t("prompts.edit_title") : t("prompts.new_title")}
          </h3>
          <button onClick={onClose} className="p-1 text-zinc-500 hover:text-zinc-300"><X size={16} /></button>
        </div>
        <div className="p-5 space-y-3">
          <input className={field} placeholder={t("prompts.field_title")} value={title}
            onChange={(e) => setTitle(e.target.value)} maxLength={200} autoFocus />
          <select className={field} value={category} onChange={(e) => setCategory(e.target.value as PromptCategory)}>
            {PROMPT_CATEGORIES.map((c) => <option key={c} value={c}>{t(`prompts.cat.${c}`)}</option>)}
          </select>
          <textarea className={`${field} resize-none`} rows={4} placeholder={t("prompts.field_prompt")}
            value={prompt} onChange={(e) => setPrompt(e.target.value)} />
          <textarea className={`${field} resize-none`} rows={2} placeholder={t("prompts.field_style_anchor")}
            value={styleAnchor} onChange={(e) => setStyleAnchor(e.target.value)} />
          <input className={field} placeholder={t("prompts.field_model")} value={model}
            onChange={(e) => setModel(e.target.value)} maxLength={200} />
          <input className={field} placeholder={t("prompts.field_tags")} value={tags}
            onChange={(e) => setTags(e.target.value)} />
          <textarea className={`${field} resize-none`} rows={2} placeholder={t("prompts.field_notes")}
            value={notes} onChange={(e) => setNotes(e.target.value)} />
          <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
            <input type="checkbox" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)}
              className="accent-violet-500" />
            {t("prompts.field_public")}
          </label>
        </div>
        <div className="flex justify-end gap-2 px-5 py-3 border-t border-white/10">
          <button onClick={onClose} className="px-3 py-1.5 rounded-lg text-sm text-zinc-400 hover:text-zinc-200">
            {t("prompts.cancel")}
          </button>
          <button onClick={submit} disabled={!title.trim() || !prompt.trim() || busy}
            className="px-4 py-1.5 rounded-lg text-sm bg-gradient-to-r from-[var(--hh-accent-from)] to-[var(--hh-accent-to)] text-white disabled:opacity-30 transition-all">
            {t("prompts.save")}
          </button>
        </div>
      </div>
    </div>
  )
}
