import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { api } from "@/shared/api-client"

interface Note {
  id: number
  text: string
  created_at: string
}

export function ExamplePage() {
  const { t } = useTranslation("example")
  const [notes, setNotes] = useState<Note[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchNotes = () => {
    setLoading(true)
    setError(null)
    api
      .get<Note[]>("/modules/example/notes")
      .then((data) => setNotes(data))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchNotes()
  }, [])

  const handleAdd = () => {
    const text = input.trim()
    if (!text) return
    setAdding(true)
    setError(null)
    api
      .post<Note>("/modules/example/notes", { text })
      .then(() => {
        setInput("")
        fetchNotes()
      })
      .catch((e) => setError(String(e)))
      .finally(() => setAdding(false))
  }

  return (
    <div className="p-6 space-y-6 max-w-2xl mx-auto">
      <h1 className="text-lg font-semibold text-zinc-100">{t("title")}</h1>

      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          placeholder={t("placeholder")}
          className="flex-1 rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-white/20"
        />
        <button
          onClick={handleAdd}
          disabled={adding || !input.trim()}
          className="rounded-lg bg-zinc-700 px-4 py-2 text-sm text-zinc-100 hover:bg-zinc-600 disabled:opacity-40 transition-colors"
        >
          {t("add")}
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="h-24 rounded-xl bg-zinc-900/50 animate-pulse" />
      ) : notes.length === 0 ? (
        <p className="text-sm text-zinc-500">{t("empty")}</p>
      ) : (
        <ul className="space-y-2">
          {notes.map((note) => (
            <li
              key={note.id}
              className="rounded-lg border border-white/8 bg-zinc-900/60 px-4 py-3 text-sm text-zinc-200"
            >
              {note.text}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
