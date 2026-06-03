import { useRef, useState, type CSSProperties } from "react"
import { useTranslation } from "react-i18next"
import { Hash, Pencil, Plus, Trash2, UserPlus, Users, X } from "lucide-react"
import { mxidToName } from "./_format"
import type { RoomAgent, TeamRoom } from "./types"

interface RoomListProps {
  accent: string
  rooms: TeamRoom[]
  currentRoomId: string | null
  members: string[]
  agents: RoomAgent[]
  me: string | null
  isAdmin: boolean
  canManage: boolean
  onSelect: (roomId: string) => void
  onCreateRoom: (name: string, memberCsv: string) => Promise<void>
  onRenameRoom: (roomId: string, name: string) => Promise<void>
  onDeleteRoom: (roomId: string) => Promise<void>
  onAddMember: (userId: string) => Promise<void>
  onRemoveMember: (userId: string) => Promise<void>
}

export function RoomList(props: RoomListProps) {
  const { accent, rooms, currentRoomId, members, agents, me, isAdmin, canManage } = props
  const { onSelect, onCreateRoom, onRenameRoom, onDeleteRoom, onAddMember, onRemoveMember } = props
  const { t } = useTranslation("teamchat")
  const [adding, setAdding] = useState(false)
  const [name, setName] = useState("")
  const [memberCsv, setMemberCsv] = useState("")
  const [busy, setBusy] = useState(false)
  const [addingMember, setAddingMember] = useState(false)
  const [memberName, setMemberName] = useState("")
  const [memberBusy, setMemberBusy] = useState(false)
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState("")
  // Ref entkoppelt das Dedup von React-Batching: Enter ruft saveRename, das
  // Unmount löst zusätzlich onBlur aus — der zweite Aufruf sieht ref=null.
  const renamingRef = useRef<string | null>(null)

  function startRename(r: TeamRoom) {
    renamingRef.current = r.room_id
    setRenamingId(r.room_id)
    setRenameValue(r.name)
  }

  function cancelRename() {
    renamingRef.current = null
    setRenamingId(null)
  }

  async function saveRename() {
    const id = renamingRef.current
    renamingRef.current = null
    setRenamingId(null)
    const v = renameValue.trim()
    if (id && v) await onRenameRoom(id, v)
  }

  async function deleteRoom(r: TeamRoom) {
    if (!confirm(t("delete_room_confirm", { name: r.name }))) return
    await onDeleteRoom(r.room_id)
  }

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

  async function addMember() {
    const u = memberName.trim()
    if (!u) return
    setMemberBusy(true)
    try {
      await onAddMember(u)
      setMemberName(""); setAddingMember(false)
    } finally {
      setMemberBusy(false)
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
          {rooms.map((r) => {
            const manageable = r.created_by === me || isAdmin
            if (renamingId === r.room_id) {
              return (
                <input
                  key={r.room_id}
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") void saveRename()
                    if (e.key === "Escape") cancelRename()
                  }}
                  onBlur={() => void saveRename()}
                  autoFocus
                  className="w-full bg-white/[6%] border border-[#104E8B]/70 rounded-lg px-2.5 py-1.5 text-sm text-zinc-100 focus:outline-none"
                />
              )
            }
            return (
              <div
                key={r.room_id}
                className={`group flex items-center rounded-lg transition-all ${
                  r.room_id === currentRoomId
                    ? "bg-[#104E8B]/40 text-zinc-100"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[5%]"
                }`}
              >
                <button
                  onClick={() => onSelect(r.room_id)}
                  className="flex-1 min-w-0 flex items-center gap-2 px-2.5 py-1.5 text-sm text-left"
                >
                  <Hash size={13} className="shrink-0 opacity-60" />
                  <span className="truncate">{r.name}</span>
                </button>
                {manageable && (
                  <div className="flex items-center pr-1.5 gap-0.5 opacity-0 group-hover:opacity-100 transition-all">
                    <button
                      onClick={() => startRename(r)}
                      title={t("rename_room")}
                      className="p-1 rounded text-zinc-500 hover:text-zinc-200"
                    >
                      <Pencil size={12} />
                    </button>
                    <button
                      onClick={() => deleteRoom(r)}
                      title={t("delete_room")}
                      className="p-1 rounded text-zinc-500 hover:text-rose-300"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>

      <div className="box box-static overflow-hidden" style={{ "--c": accent } as CSSProperties}>
        <div className="box-h">
          <span className="ic"><Users size={14} /></span>
          <span className="t">{t("members")}</span>
          {canManage && currentRoomId && (
            <button
              onClick={() => setAddingMember((v) => !v)}
              title={t("add_member")}
              className="r p-1 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-white/[6%] transition-all"
            >
              <UserPlus size={14} />
            </button>
          )}
        </div>
        <div className="box-b !py-2">
          {addingMember && (
            <div className="flex gap-1.5 mb-2">
              <input
                value={memberName} onChange={(e) => setMemberName(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") void addMember() }}
                placeholder={t("member_username")} autoFocus
                className="flex-1 min-w-0 bg-white/[5%] border border-white/[8%] rounded-md px-2 py-1 text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none"
              />
              <button
                onClick={addMember} disabled={memberBusy || !memberName.trim()}
                className="shrink-0 text-xs px-2 py-1 rounded-md bg-[#104E8B]/60 text-zinc-100 hover:bg-[#104E8B]/80 disabled:opacity-30 transition-all"
              >
                {t("add")}
              </button>
            </div>
          )}
          {members.length === 0 && (
            <p className="text-xs text-zinc-500 italic">{t("no_members")}</p>
          )}
          {humans.map((mxid) => {
            const username = mxidToName(mxid).name
            return (
              <div key={mxid} className="flex items-center gap-2 py-1 group">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]" />
                <span className="text-xs text-zinc-300 flex-1 truncate">{username}</span>
                {canManage && username !== me && (
                  <button
                    onClick={() => onRemoveMember(username)}
                    title={t("remove_member")}
                    className="p-0.5 rounded text-zinc-600 hover:text-rose-300 opacity-0 group-hover:opacity-100 transition-all"
                  >
                    <X size={12} />
                  </button>
                )}
              </div>
            )
          })}
          {bots.map((mxid) => {
            const lp = mxidToName(mxid).name
            const label = agents.find((a) => a.agent_id === lp)?.name ?? lp
            return (
              <div key={mxid} className="flex items-center gap-2 py-1">
                <span className="text-[10px]">🐙</span>
                <span className="text-xs text-[var(--hh-accent-text)]">{label}</span>
              </div>
            )
          })}
        </div>
      </div>
    </>
  )
}
