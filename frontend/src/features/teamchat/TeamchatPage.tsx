import { useTranslation } from "react-i18next"
import { Loader2, MessagesSquare } from "lucide-react"
import { Link } from "react-router-dom"
import { HydraMascot } from "@/shared/HydraMascot"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { rgbFor } from "@/shared/colors"
import { useTeamchat } from "./useTeamchat"
import { RoomList } from "./_RoomList"
import { ChatView } from "./_ChatView"
import { AgentPanel } from "./_AgentPanel"

export function TeamchatPage() {
  const { t } = useTranslation("teamchat")
  const tc = useTeamchat()
  const accent = rgbFor("/teamchat")
  const me = useAuthStore((s) => s.username)
  const role = useAuthStore((s) => s.role)

  if (tc.loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <HydraMascot state="sleeping" size={110} animate />
        <Loader2 size={16} className="text-zinc-500 animate-spin" />
      </div>
    )
  }

  if (tc.notConfigured) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3 text-center px-4">
        <HydraMascot state="sleeping" size={120} />
        <p className="text-sm text-zinc-300">{t("not_configured")}</p>
        <p className="text-xs text-zinc-500 max-w-sm">{t("not_configured_hint")}</p>
        <Link to="/extensions" className="text-xs text-[var(--hh-accent-text)] hover:underline">
          {t("to_extensions")} →
        </Link>
      </div>
    )
  }

  if (tc.error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <HydraMascot state="error" size={120} />
        <p className="text-sm text-rose-300">{tc.error}</p>
      </div>
    )
  }

  const currentRoom = tc.rooms.find((r) => r.room_id === tc.currentRoomId) ?? null
  const canManage = !!currentRoom && (currentRoom.created_by === me || role === "admin")

  return (
    <div className="flex items-stretch h-full gap-4 px-4 py-4 overflow-hidden">
      <aside className="hidden lg:flex flex-col gap-4 w-60 shrink-0 overflow-y-auto min-h-0">
        <RoomList
          accent={accent}
          rooms={tc.rooms}
          currentRoomId={tc.currentRoomId}
          members={tc.members}
          agents={tc.roomAgents}
          me={me}
          canManage={canManage}
          onSelect={tc.selectRoom}
          onCreateRoom={tc.createRoom}
          onAddMember={tc.addMember}
          onRemoveMember={tc.removeMember}
        />
      </aside>

      <div className="flex-1 flex flex-col min-w-0 min-h-0">
        {currentRoom ? (
          <ChatView roomName={currentRoom.name} messages={tc.messages} agents={tc.roomAgents} onSend={tc.send} />
        ) : (
          <div className="flex flex-col items-center justify-center flex-1 gap-3 text-center">
            <MessagesSquare size={56} className="text-zinc-700" />
            <p className="text-sm text-zinc-400">{t("no_room_selected")}</p>
            <p className="text-xs text-zinc-600">{t("no_room_selected_hint")}</p>
          </div>
        )}
      </div>

      <aside className="hidden lg:flex flex-col gap-4 w-60 shrink-0 overflow-y-auto min-h-0">
        <AgentPanel
          accent={accent}
          roomAgents={tc.roomAgents}
          ownAgents={tc.ownAgents}
          onAttach={tc.attachAgent}
          onDetach={tc.detachAgent}
        />
      </aside>
    </div>
  )
}
