import { useState, type CSSProperties } from "react"
import { useTranslation } from "react-i18next"
import { Hash, Plus, Users } from "lucide-react"
import { mxidToName } from "./_format"
import type { TeamRoom } from "./types"

interface RoomListProps {
  accent: string
  rooms: TeamRoom[]
  currentRoomId: string | null
  members: string[]
  onSelect: (roomId: string) => void
  onCreateRoom: (name: string, memberCsv: string) => Promise<void>
}

export function RoomList({ accent, rooms, currentRoomId, members, onSelect, onCreateRoom }: RoomListProps) {
  const { t } = useTranslation("teamchat")
  const [adding, setAdding] = useState(false)
  const [name, setName] = useState("")
  const [memberCsv, setMemberCsv] = useState("")
  const [busy, setBusy] = useState(false)

  async function create() {
    if (!name.trim()) return
    setBusy(true)
    try {
      await onCreateRoom(name.trim(), memberCsv)
      setName(""); setMemberCsv(""); setAdding(false)
    } finally {
      setBusy(false)
    }
  }

  const humans = members.filter((m) => !mxidToName(m).isBot)
  const bots = members.filter((m) => mxidToName(m).isBot)

  return (
    <>
      <div className="box box-static overflow-hidden" style={{ "--c": accent } as CSSProperties}>
        <div className="box-h">
          <span className="ic"><Hash size={14} /></span>
          <span className="t">{t("rooms")}</span>
          <button
            onClick={() => setAdding((v) => !v)}
            title={t("new_room")}
            className="r p-1 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-white/[6%] transition-all"
          >
            <Plus size={14} />
          </button>
        </div>
        <div className="box-b !p-1.5">
          {adding && (
            <div className="flex flex-col gap-1.5 p-2 mb-1.5 rounded-lg bg-white/[3%] border border-white/[6%]">
              <input
                value={name} onChange={(e) => setName(e.target.value)}
                placeholder={t("room_name")} autoFocus
                className="bg-white/[5%] border border-white/[8%] rounded-md px-2 py-1 text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none"
              />
              <input
                value={memberCsv} onChange={(e) => setMemberCsv(e.target.value)}
                placeholder={t("members_csv")}
                className="bg-white/[5%] border border-white/[8%] rounded-md px-2 py-1 text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none"
              />
              <button
                onClick={create} disabled={busy || !name.trim()}
                className="text-xs px-2 py-1 rounded-md bg-[#104E8B]/60 text-zinc-100 hover:bg-[#104E8B]/80 disabled:opacity-30 transition-all"
              >
                {t("create")}
              </button>
            </div>
          )}
          {rooms.length === 0 && !adding && (
            <p className="text-xs text-zinc-500 italic px-2 py-3 text-center">{t("no_rooms")}</p>
          )}
          {rooms.map((r) => (
            <button
              key={r.room_id}
              onClick={() => onSelect(r.room_id)}
              className={`w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-sm transition-all ${
                r.room_id === currentRoomId
                  ? "bg-[#104E8B]/40 text-zinc-100"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[5%]"
              }`}
            >
              <Hash size={13} className="shrink-0 opacity-60" />
              <span className="truncate">{r.name}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="box box-static overflow-hidden" style={{ "--c": accent } as CSSProperties}>
        <div className="box-h">
          <span className="ic"><Users size={14} /></span>
          <span className="t">{t("members")}</span>
        </div>
        <div className="box-b !py-2">
          {members.length === 0 && (
            <p className="text-xs text-zinc-500 italic">{t("no_members")}</p>
          )}
          {humans.map((mxid) => (
            <div key={mxid} className="flex items-center gap-2 py-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]" />
              <span className="text-xs text-zinc-300">{mxidToName(mxid).name}</span>
            </div>
          ))}
          {bots.map((mxid) => (
            <div key={mxid} className="flex items-center gap-2 py-1">
              <span className="text-[10px]">🐙</span>
              <span className="text-xs text-[var(--hh-accent-text)]">{mxidToName(mxid).name}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  )
}
