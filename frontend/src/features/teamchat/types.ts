export interface TeamRoom {
  room_id: string
  name: string
  created_by: string
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
