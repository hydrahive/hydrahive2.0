import { useTranslation } from "react-i18next"
import { Pencil, Trash2, Globe } from "lucide-react"
import type { PromptEntry } from "./promptArchive"

interface Props {
  entry: PromptEntry
  /** True wenn der eingeloggte User der Besitzer ist (Edit/Delete nur dann). */
  owned: boolean
  onUse: (entry: PromptEntry) => void
  onEdit: (entry: PromptEntry) => void
  onDelete: (entry: PromptEntry) => void
}

/** Eine Zeile in der Prompt-Liste: Titel + Tags links, Aktionen rechts. */
export function PromptRow({ entry, owned, onUse, onEdit, onDelete }: Props) {
  const { t } = useTranslation("chat")
  return (
    <div className="group flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/[5%]">
      <button onClick={() => onUse(entry)} className="flex-1 min-w-0 text-left" title={t("prompts.use")}>
        <div className="flex items-center gap-1.5">
          <span className="text-sm text-zinc-200 truncate">{entry.title}</span>
          {entry.is_public && <Globe size={11} className="text-emerald-400/70 flex-shrink-0" />}
        </div>
        <div className="flex items-center gap-1 mt-0.5">
          {entry.tags.slice(0, 3).map((tag) => (
            <span key={tag} className="text-[10px] px-1.5 py-px rounded bg-white/[6%] text-zinc-500">{tag}</span>
          ))}
          {entry.use_count > 0 && (
            <span className="text-[10px] text-zinc-600">· {t("prompts.used_n", { n: entry.use_count })}</span>
          )}
        </div>
      </button>
      {owned && (
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
          <button onClick={() => onEdit(entry)} title={t("prompts.edit")}
            className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/10">
            <Pencil size={13} />
          </button>
          <button onClick={() => onDelete(entry)} title={t("prompts.delete")}
            className="p-1 rounded text-zinc-500 hover:text-rose-400 hover:bg-white/10">
            <Trash2 size={13} />
          </button>
        </div>
      )}
    </div>
  )
}
