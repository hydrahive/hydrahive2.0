import { useState } from "react"
import { ChevronDown } from "lucide-react"
import type { Session } from "./types"

interface Props {
  session: Session
  sessions: Session[]
  activeSessionId: string | null
  onSelectSession: (sessionId: string) => void
}

/** Auswahl der Projekt-Session im Chat-Kopf des Projekt-Cockpits.
 * Auf dem Handy schmal (docs/specs/chat-mobile-compact.md). */
export function SessionMenu({ session, sessions, activeSessionId, onSelectSession }: Props) {
  const [open, setOpen] = useState(false)
  return (
    <div className="relative min-w-0">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex max-w-[140px] items-center gap-2 rounded-[4px] border border-s-rand bg-s-tief px-2.5 py-1.5 text-xs font-semibold text-[#e8eef8] outline-none hover:border-s-rand-hover sm:max-w-[240px]"
        title="Projekt-Session wählen"
      >
        <span className="truncate">{session.title || "Neue Session"}</span>
        <ChevronDown size={12} className="shrink-0 text-[#9aa7bc]" />
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-1 max-h-[320px] w-[min(280px,calc(100vw-2rem))] overflow-y-auto rounded-[4px] border border-s-rand bg-s-box p-1 shadow-2xl shadow-black/50">
          {sessions.map((item) => {
            const active = item.id === (activeSessionId ?? session.id)
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => { onSelectSession(item.id); setOpen(false) }}
                className={[
                  "block w-full truncate rounded-[4px] px-2.5 py-2 text-left text-xs font-semibold transition-colors",
                  active ? "bg-[#1c2940] text-[#69d7ff]" : "text-[#cdd7e6] hover:bg-s-hebung hover:text-[#e8eef8]",
                ].join(" ")}
              >
                {item.title || "Neue Session"}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
