export type RoomVisibility = "private" | "open"

export interface TeamRoom {
  room_id: string
  name: string
  created_by: string
  visibility: RoomVisibility
  created_at?: string
}

export interface TeamMessage {
  event_id: string
  sender: string
  text: string
  ts?: number
}

export interface RoomAgent {
  agent_id: string
  name: string | null
}
