import { useCallback, useEffect, useState } from "react"
import { agentsApi } from "@/features/agents/api"
import type { Agent } from "@/features/agents/types"
import { streamRoom, teamchatApi } from "./api"
import type { RoomAgent, TeamMessage, TeamRoom } from "./types"

export function useTeamchat() {
  const [rooms, setRooms] = useState<TeamRoom[]>([])
  const [currentRoomId, setCurrentRoomId] = useState<string | null>(null)
  const [messages, setMessages] = useState<TeamMessage[]>([])
  const [members, setMembers] = useState<string[]>([])
  const [roomAgents, setRoomAgents] = useState<RoomAgent[]>([])
  const [ownAgents, setOwnAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [notConfigured, setNotConfigured] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Initial: Räume + eigene Agenten (für den Picker)
  useEffect(() => {
    let alive = true
    teamchatApi.listRooms()
      .then((rs) => {
        if (!alive) return
        setRooms(rs)
        setCurrentRoomId((cur) => cur ?? rs[0]?.room_id ?? null)
      })
      .catch((e: unknown) => {
        if (!alive) return
        if ((e as { status?: number }).status === 409) setNotConfigured(true)
        else setError(e instanceof Error ? e.message : "Fehler")
      })
      .finally(() => { if (alive) setLoading(false) })
    agentsApi.list().then((a) => { if (alive) setOwnAgents(a) }).catch(() => {})
    return () => { alive = false }
  }, [])

  const refreshRoomContext = useCallback((roomId: string) => {
    teamchatApi.getMembers(roomId).then(setMembers).catch(() => setMembers([]))
    teamchatApi.getRoomAgents(roomId).then(setRoomAgents).catch(() => setRoomAgents([]))
  }, [])

  // Raumwechsel: History + Mitglieder + Agenten laden. Jede Resolution ist mit
  // `alive` abgesichert — eine langsame Antwort des ALTEN Raums darf den neuen
  // nicht überschreiben (Wrong-Room-Race).
  useEffect(() => {
    if (!currentRoomId) return
    const roomId = currentRoomId
    let alive = true
    teamchatApi.getMessages(roomId).then((m) => { if (alive) setMessages(m) }).catch(() => { if (alive) setMessages([]) })
    teamchatApi.getMembers(roomId).then((m) => { if (alive) setMembers(m) }).catch(() => { if (alive) setMembers([]) })
    teamchatApi.getRoomAgents(roomId).then((a) => { if (alive) setRoomAgents(a) }).catch(() => { if (alive) setRoomAgents([]) })
    return () => { alive = false }
  }, [currentRoomId])

  // Live-Stream pro Raum — dedupe über event_id (robust gegen Reconnect-Replays
  // und den Eigen-Broadcast der POST-Route). `active`-Guard: ein Rest-Batch des
  // alten Streams nach Raumwechsel darf nicht in den neuen Raum tropfen.
  useEffect(() => {
    if (!currentRoomId) return
    let active = true
    const stop = streamRoom(
      currentRoomId,
      (msg) => { if (active) setMessages((prev) =>
        prev.some((m) => m.event_id === msg.event_id) ? prev : [...prev, msg]) },
      () => { /* Stream-Fehler: still — History ist bereits geladen */ },
    )
    return () => { active = false; stop() }
  }, [currentRoomId])

  const selectRoom = useCallback((roomId: string) => setCurrentRoomId(roomId), [])

  const send = useCallback(async (text: string) => {
    if (!currentRoomId || !text.trim()) return
    // KEIN optimistisches Append: die POST-Route broadcastet an alle Abonnenten
    // (inkl. Absender), der SSE-Kanal liefert die Nachricht zurück.
    await teamchatApi.sendMessage(currentRoomId, text)
  }, [currentRoomId])

  const createRoom = useCallback(async (name: string, memberCsv: string) => {
    const members = memberCsv.split(",").map((s) => s.trim()).filter(Boolean)
    const { room_id } = await teamchatApi.createRoom(name, members)
    setRooms(await teamchatApi.listRooms())
    setCurrentRoomId(room_id)
  }, [])

  const renameRoom = useCallback(async (roomId: string, name: string) => {
    await teamchatApi.renameRoom(roomId, name)
    setRooms(await teamchatApi.listRooms())
  }, [])

  const deleteRoom = useCallback(async (roomId: string) => {
    await teamchatApi.deleteRoom(roomId)
    try {
      const rs = await teamchatApi.listRooms()
      setRooms(rs)
      setCurrentRoomId((cur) => (cur === roomId ? (rs[0]?.room_id ?? null) : cur))
    } catch {
      // Refresh schlug fehl → trotzdem lokal entfernen (Raum ist serverseitig weg)
      setRooms((prev) => prev.filter((r) => r.room_id !== roomId))
      setCurrentRoomId((cur) => (cur === roomId ? null : cur))
    }
  }, [])

  const addMember = useCallback(async (userId: string) => {
    if (!currentRoomId) return
    await teamchatApi.inviteMember(currentRoomId, userId)
    refreshRoomContext(currentRoomId)
  }, [currentRoomId, refreshRoomContext])

  const removeMember = useCallback(async (userId: string) => {
    if (!currentRoomId) return
    await teamchatApi.kickMember(currentRoomId, userId)
    refreshRoomContext(currentRoomId)
  }, [currentRoomId, refreshRoomContext])

  const attachAgent = useCallback(async (agentId: string) => {
    if (!currentRoomId) return
    await teamchatApi.attachAgent(currentRoomId, agentId)
    refreshRoomContext(currentRoomId)
  }, [currentRoomId, refreshRoomContext])

  const detachAgent = useCallback(async (agentId: string) => {
    if (!currentRoomId) return
    await teamchatApi.detachAgent(currentRoomId, agentId)
    refreshRoomContext(currentRoomId)
  }, [currentRoomId, refreshRoomContext])

  return {
    rooms, currentRoomId, messages, members, roomAgents, ownAgents,
    loading, notConfigured, error,
    selectRoom, send, createRoom, renameRoom, deleteRoom, attachAgent, detachAgent, addMember, removeMember,
  }
}
