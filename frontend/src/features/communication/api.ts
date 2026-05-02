import { api } from "@/shared/api-client"

export type ChannelState =
  | "disconnected"
  | "connecting"
  | "waiting_qr"
  | "connected"
  | "error"

export interface ChannelStatus {
  connected: boolean
  state: ChannelState
  detail: string | null
  qr_data_url: string | null
}

export interface WhatsAppConfig {
  private_chats_enabled: boolean
  group_chats_enabled: boolean
  require_keyword: string
  owner_numbers: string[]
  allowed_numbers: string[]
  blocked_numbers: string[]
  respond_as_voice: boolean
  voice_name: string
  stt_language: string  // "" oder "auto" = Whisper-Auto-Detect, sonst ISO ("de","en",...)
}

export interface DiscordConfig {
  bot_token: string
  dm_enabled: boolean
  mention_enabled: boolean
  require_keyword: string
  allowed_user_ids: string[]
  blocked_user_ids: string[]
  allowed_channel_ids: string[]
  respond_as_voice: boolean
  voice_name: string
}

export const communicationApi = {
  channels: () => api.get<{ name: string; label: string }[]>("/communication/channels"),
  discord: {
    status: () => api.get<ChannelStatus>("/communication/discord/status"),
    connect: () => api.post<ChannelStatus>("/communication/discord/connect", {}),
    disconnect: () => api.post<{ ok: boolean }>("/communication/discord/disconnect", {}),
    getConfig: () => api.get<DiscordConfig>("/communication/discord/config"),
    putConfig: (cfg: DiscordConfig) =>
      api.put<DiscordConfig>("/communication/discord/config", cfg),
  },
  whatsapp: {
    status: () => api.get<ChannelStatus>("/communication/whatsapp/status"),
    connect: () => api.post<ChannelStatus>("/communication/whatsapp/connect", {}),
    disconnect: () => api.post<{ ok: boolean }>("/communication/whatsapp/disconnect", {}),
    getConfig: () => api.get<WhatsAppConfig>("/communication/whatsapp/config"),
    putConfig: (cfg: WhatsAppConfig) =>
      api.put<WhatsAppConfig>("/communication/whatsapp/config", cfg),
  },
}
