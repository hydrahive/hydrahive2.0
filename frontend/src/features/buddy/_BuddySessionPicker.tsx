// Auswahl früherer Buddy-Unterhaltungen im Kopf des Buddy-Chats
// (docs/specs/buddy-session-picker.md). Nur Web-Unterhaltungen; Öffnen lädt
// wie bisher nur das Ende der Unterhaltung (useChat, letzte 400 Nachrichten).
import { ChevronDown, History, Loader2 } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { buddyApi, type BuddySessionRow, type BuddyState } from "./api"
import { sessionMeta, sessionTitle } from "./_buddySessionLabel"

const PAGE = 30

interface Props {
  activeId: string | null
  disabled: boolean
  onOpened: (state: BuddyState) => void
}

export function BuddySessionPicker({ activeId, disabled, onOpened }: Props) {
  const [open, setOpen] = useState(false)
  const [rows, setRows] = useState<BuddySessionRow[]>([])
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const box = useRef<HTMLDivElement>(null)

  // Antwort übernehmen — nur aus Promise-Callbacks, nie synchron im Effekt.
  const apply = (offset: number) => (res: Awaited<ReturnType<typeof buddyApi.sessions>>) => {
    setRows((prev) => (offset === 0 ? res.sessions : [...prev, ...res.sessions]))
    setHasMore(res.has_more)
    setError(null)
  }
  const fail = () => setError("Unterhaltungen konnten nicht geladen werden")

  function loadMore() {
    setLoading(true)
    buddyApi.sessions(rows.length, PAGE).then(apply(rows.length), fail).finally(() => setLoading(false))
  }

  // Beim Start und bei jedem Wechsel/Neuer Chat laden (Titel im Knopf), beim
  // Aufklappen frisch (neue Nachrichten ändern die Reihenfolge).
  useEffect(() => {
    let alive = true
    buddyApi.sessions(0, PAGE).then((res) => { if (alive) apply(0)(res) }, () => { if (alive) fail() })
    return () => { alive = false }
  }, [activeId, open])

  // Klick außerhalb schließt.
  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false) }
    document.addEventListener("mousedown", close)
    return () => document.removeEventListener("mousedown", close)
  }, [open])

  async function pick(id: string) {
    if (id === activeId) { setOpen(false); return }
    setLoading(true)
    try {
      onOpened(await buddyApi.openSession(id))
      setOpen(false)
    } catch {
      setError("Unterhaltung konnte nicht geöffnet werden (läuft gerade noch etwas?)")
    } finally {
      setLoading(false)
    }
  }

  const current = rows.find((r) => r.id === activeId)
  // Sichtbar als Knopf (Rahmen + Fläche wie die Nachbarn im Kopf), nicht nur
  // grauer Text — Till 03.10.2026: „man sieht sie sehr schlecht“.
  return (
    <div ref={box} className="relative min-w-0 shrink">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        title="Frühere Unterhaltungen"
        aria-expanded={open}
        className={`flex w-full max-w-[24rem] min-w-0 items-center gap-1.5 rounded-[4px] border px-2 py-0.5 text-xs font-medium transition-colors disabled:opacity-40 ${open
          ? "border-fuchsia-400/60 bg-fuchsia-500/20 text-fuchsia-100"
          : "border-fuchsia-400/35 bg-fuchsia-500/10 text-fuchsia-100 hover:border-fuchsia-400/60 hover:bg-fuchsia-500/20"}`}
      >
        <History size={13} className="shrink-0 text-fuchsia-300" />
        <span className="shrink-0 text-fuchsia-300/80">Verlauf:</span>
        <span className="truncate">{current ? sessionTitle(current) : "frühere Unterhaltungen"}</span>
        <ChevronDown size={13} className={`shrink-0 text-fuchsia-300 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div role="listbox" aria-label="Frühere Unterhaltungen"
          className="absolute left-0 top-6 z-30 max-h-[24rem] w-[24rem] overflow-y-auto rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-1 shadow-xl">
          {rows.map((r) => (
            <button key={r.id} type="button" role="option" aria-selected={r.id === activeId}
              onClick={() => void pick(r.id)}
              className={`block w-full rounded-[3px] px-2 py-1.5 text-left ${r.id === activeId
                ? "bg-fuchsia-500/15 text-[#e8eef8]" : "text-[#c4cedd] hover:bg-[#172133]"}`}>
              <span className="block truncate text-xs" title={r.first_message ?? undefined}>{sessionTitle(r)}</span>
              <span className="block text-[10px] text-[#8d9ab0]">{sessionMeta(r)}</span>
            </button>
          ))}
          {error && <p className="px-2 py-1.5 text-[11px] text-rose-300">{error}</p>}
          {loading && <p className="flex items-center gap-1 px-2 py-1.5 text-[11px] text-[#8d9ab0]"><Loader2 size={11} className="animate-spin" /> lädt …</p>}
          {!loading && hasMore && (
            <button type="button" onClick={loadMore}
              className="w-full px-2 py-1.5 text-left text-[11px] text-[#69d7ff] hover:underline">Weitere laden</button>
          )}
          {!loading && !error && rows.length === 0 && <p className="px-2 py-1.5 text-[11px] text-[#8d9ab0]">Noch keine Unterhaltungen</p>}
        </div>
      )}
    </div>
  )
}
