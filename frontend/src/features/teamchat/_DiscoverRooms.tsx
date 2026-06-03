import { useState, type CSSProperties } from "react"
import { useTranslation } from "react-i18next"
import { Globe, Plus } from "lucide-react"
import type { TeamRoom } from "./types"

interface DiscoverRoomsProps {
  accent: string
  openRooms: TeamRoom[]
  onJoinRoom: (roomId: string) => Promise<void>
}

/** Offene Räume, in denen der User noch nicht ist — beitretbar per Klick. */
export function DiscoverRooms({ accent, openRooms, onJoinRoom }: DiscoverRoomsProps) {
  const { t } = useTranslation("teamchat")
  const [busyId, setBusyId] = useState<string | null>(null)

  if (openRooms.length === 0) return null

  async function join(roomId: string) {
    setBusyId(roomId)
    try { await onJoinRoom(roomId) } finally { setBusyId(null) }
  }

  return (
    <div className="box box-static overflow-hidden" style={{ "--c": accent } as CSSProperties}>
      <div className="box-h">
        <span className="ic"><Globe size={14} /></span>
        <span className="t">{t("discover")}</span>
      </div>
      <div className="box-b !p-1.5">
        {openRooms.map((r) => (
          <div key={r.room_id} className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-sm text-zinc-400 group">
            <Globe size={13} className="shrink-0 opacity-60" />
            <span className="truncate flex-1">{r.name}</span>
            <button
              onClick={() => join(r.room_id)}
              disabled={busyId === r.room_id}
              title={t("join_room")}
              className="shrink-0 inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-[#104E8B]/40 text-[var(--hh-accent-text)] hover:bg-[#104E8B]/60 transition-all disabled:opacity-40"
            >
              <Plus size={11} /> {t("join")}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
