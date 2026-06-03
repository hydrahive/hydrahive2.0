import { useAuthStore } from "@/features/auth/useAuthStore"
import { api } from "@/shared/api-client"
import type { RoomAgent, RoomVisibility, TeamMessage, TeamRoom } from "./types"

function authHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function roomPath(roomId: string, suffix = ""): string {
  // room_id enthält "!" und ":" → als ein Pfadsegment kodieren.
  return `/teamchat/rooms/${encodeURIComponent(roomId)}${suffix}`
}

export const teamchatApi = {
  listRooms: () => api.get<TeamRoom[]>("/teamchat/rooms"),
  listOpenRooms: () => api.get<TeamRoom[]>("/teamchat/rooms/open"),
  createRoom: (name: string, members: string[], visibility: RoomVisibility = "private") =>
    api.post<{ room_id: string }>("/teamchat/rooms", { name, members, visibility }),
  joinRoom: (roomId: string) => api.post<void>(roomPath(roomId, "/join"), {}),
  renameRoom: (roomId: string, name: string) =>
    api.patch<void>(roomPath(roomId), { name }),
  deleteRoom: (roomId: string) => api.delete<void>(roomPath(roomId)),

  getMessages: (roomId: string, limit = 50) =>
    api.get<TeamMessage[]>(roomPath(roomId, `/messages?limit=${limit}`)),
  sendMessage: (roomId: string, text: string) =>
    api.post<TeamMessage>(roomPath(roomId, "/messages"), { text }),

  getPresence: () => api.get<{ online: string[] }>("/teamchat/presence"),
  getMembers: (roomId: string) => api.get<string[]>(roomPath(roomId, "/members")),
  inviteMember: (roomId: string, userId: string) =>
    api.post<void>(roomPath(roomId, "/members"), { user_id: userId }),
  kickMember: (roomId: string, userId: string) =>
    api.delete<void>(roomPath(roomId, `/members/${encodeURIComponent(userId)}`)),

  getRoomAgents: (roomId: string) => api.get<RoomAgent[]>(roomPath(roomId, "/agents")),
  attachAgent: (roomId: string, agentId: string) =>
    api.post<{ room_id: string; agent_id: string }>(roomPath(roomId, "/agents"), { agent_id: agentId }),
  detachAgent: (roomId: string, agentId: string) =>
    api.delete<void>(roomPath(roomId, `/agents/${encodeURIComponent(agentId)}`)),
}

/**
 * Abonniert den Live-Stream eines Raums (SSE). Liefert eine cleanup-Funktion.
 * Jede `data:`-Zeile ist eine TeamMessage; Keepalive-Kommentare (":") werden
 * ignoriert. Muster wie features/extensions/api.ts.
 */
export function streamRoom(
  roomId: string,
  onMessage: (msg: TeamMessage) => void,
  onError: (msg: string) => void,
): () => void {
  let closed = false
  const ctrl = new AbortController()

  fetch(`/api${roomPath(roomId, "/stream")}`, {
    headers: { ...authHeaders() },
    signal: ctrl.signal,
  })
    .then(async (r) => {
      if (!r.ok || !r.body) {
        onError(`HTTP ${r.status}`)
        return
      }
      const reader = r.body.getReader()
      const dec = new TextDecoder()
      let buf = ""
      while (true) {
        const { done, value } = await reader.read()
        if (done || closed) break
        buf += dec.decode(value, { stream: true })
        const parts = buf.split("\n\n")
        buf = parts.pop() ?? ""
        for (const part of parts) {
          const dataLine = part.split("\n").find((l) => l.startsWith("data:"))
          if (!dataLine) continue
          try {
            onMessage(JSON.parse(dataLine.slice(5).trim()) as TeamMessage)
          } catch {
            // Nicht-JSON (sollte nicht vorkommen) → ignorieren
          }
        }
      }
    })
    .catch((e) => {
      if (!closed) onError(e instanceof Error ? e.message : String(e))
    })

  return () => {
    closed = true
    ctrl.abort()
  }
}
