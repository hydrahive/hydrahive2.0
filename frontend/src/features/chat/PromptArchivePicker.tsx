import { useEffect, useRef, useState, useCallback } from "react"
import { useTranslation } from "react-i18next"
import { Library, Plus, Search } from "lucide-react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { promptArchiveApi, PROMPT_CATEGORIES, type PromptCategory, type PromptEntry, type PromptInput } from "./promptArchive"
import { PromptRow } from "./_PromptRow"
import { PromptEditDialog } from "./_PromptEditDialog"

interface Props {
  /** Setzt den Prompt-Text ins Eingabefeld. */
  onPick: (text: string) => void
  disabled?: boolean
}

/** Button + Overlay fürs Prompt-Archiv. Klick auf einen Eintrag schiebt den
 * Prompt (style_anchor + prompt) ins Eingabefeld und zählt use_count hoch. */
export function PromptArchivePicker({ onPick, disabled }: Props) {
  const { t } = useTranslation("chat")
  const username = useAuthStore((s) => s.username)
  const [open, setOpen] = useState(false)
  const [category, setCategory] = useState<PromptCategory | "all">("all")
  const [query, setQuery] = useState("")
  const [items, setItems] = useState<PromptEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [editing, setEditing] = useState<PromptEntry | "new" | null>(null)
  const ref = useRef<HTMLDivElement>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await promptArchiveApi.list({
        category: category === "all" ? undefined : category,
        q: query.trim() || undefined,
      })
      setItems(res.prompts)
    } finally {
      setLoading(false)
    }
  }, [category, query])

  useEffect(() => {
    if (!open) return
    load()
  }, [open, load])

  useEffect(() => {
    if (!open) return
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", onDoc)
    return () => document.removeEventListener("mousedown", onDoc)
  }, [open])

  async function handleUse(entry: PromptEntry) {
    const text = entry.style_anchor ? `${entry.style_anchor}, ${entry.prompt}` : entry.prompt
    onPick(text)
    setOpen(false)
    await promptArchiveApi.markUsed(entry.id).catch(() => {})
  }

  async function handleSave(body: PromptInput) {
    if (editing && editing !== "new") {
      await promptArchiveApi.update(editing.id, body)
    } else {
      await promptArchiveApi.create(body)
    }
    await load()
  }

  async function handleDelete(entry: PromptEntry) {
    if (!confirm(t("prompts.confirm_delete", { title: entry.title }))) return
    await promptArchiveApi.remove(entry.id)
    await load()
  }

  return (
    <div ref={ref} className="relative flex-shrink-0">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        title={t("prompts.button_title")}
        className={`p-1.5 rounded-lg transition-colors disabled:opacity-30 disabled:cursor-not-allowed ${
          open ? "text-violet-300 bg-violet-500/15" : "text-zinc-500 hover:text-zinc-300 hover:bg-white/5"
        }`}
      >
        <Library size={15} />
      </button>
      {open && (
        <div className="absolute bottom-full mb-2 left-0 z-30 w-80 rounded-xl bg-zinc-900/95 backdrop-blur border border-white/10 shadow-xl shadow-black/50 flex flex-col max-h-[400px]">
          <div className="flex items-center gap-2 p-2 border-b border-white/10">
            <div className="flex-1 flex items-center gap-1.5 rounded-lg bg-white/[4%] px-2 py-1">
              <Search size={13} className="text-zinc-500" />
              <input value={query} onChange={(e) => setQuery(e.target.value)}
                placeholder={t("prompts.search")}
                className="flex-1 bg-transparent text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none" />
            </div>
            <button onClick={() => setEditing("new")} title={t("prompts.new_title")}
              className="p-1.5 rounded-lg text-violet-300 hover:bg-violet-500/15">
              <Plus size={15} />
            </button>
          </div>
          <div className="flex items-center gap-1 px-2 py-1.5 border-b border-white/10 overflow-x-auto">
            <Tab active={category === "all"} onClick={() => setCategory("all")}>{t("prompts.cat.all")}</Tab>
            {PROMPT_CATEGORIES.map((c) => (
              <Tab key={c} active={category === c} onClick={() => setCategory(c)}>{t(`prompts.cat.${c}`)}</Tab>
            ))}
          </div>
          <div className="flex-1 overflow-y-auto p-1">
            {loading ? (
              <p className="text-xs text-zinc-600 text-center py-6">{t("prompts.loading")}</p>
            ) : items.length === 0 ? (
              <p className="text-xs text-zinc-600 text-center py-6">{t("prompts.empty")}</p>
            ) : (
              items.map((entry) => (
                <PromptRow key={entry.id} entry={entry} owned={entry.user_id === username}
                  onUse={handleUse} onEdit={setEditing} onDelete={handleDelete} />
              ))
            )}
          </div>
        </div>
      )}
      {editing && (
        <PromptEditDialog
          entry={editing === "new" ? undefined : editing}
          onSave={handleSave}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  )
}

function Tab({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick}
      className={`px-2 py-0.5 rounded-md text-xs whitespace-nowrap transition-colors ${
        active ? "bg-violet-500/20 text-violet-200" : "text-zinc-500 hover:text-zinc-300 hover:bg-white/5"
      }`}>
      {children}
    </button>
  )
}
