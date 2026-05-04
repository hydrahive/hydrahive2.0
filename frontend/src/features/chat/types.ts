export interface Session {
  id: string
  agent_id: string
  user_id: string
  project_id: string | null
  title: string | null
  status: string
  created_at: string
  updated_at: string
  metadata: Record<string, unknown>
}

export type ImageSource =
  | { type: "base64"; media_type: string; data: string }
  | { type: "url"; url: string }

export type ToolMedia = { kind: "image" | "audio" | "video"; path: string }

export type ContentBlock =
  | { type: "text"; text: string }
  | { type: "image"; source: ImageSource }
  | { type: "tool_use"; id: string; name: string; input: Record<string, unknown>; duration_ms?: number }
  | {
      type: "tool_result"
      tool_use_id: string
      content: string
      is_error?: boolean
      duration_ms?: number
      media?: ToolMedia[]
      tool_name?: string
    }

export interface Message {
  id: string
  role: "user" | "assistant" | "tool" | "system" | "compaction"
  content: string | ContentBlock[]
  created_at: string
  token_count: number | null
  metadata: Record<string, unknown>
}

export interface AgentBrief {
  id: string
  name: string
  type: string
  llm_model: string
  status: string
  is_buddy?: boolean
}

export type RunnerEvent =
  | { type: "iteration_start"; iteration: number }
  | { type: "message_start" }
  | { type: "text_delta"; text: string }
  | { type: "text"; text: string }
  | {
      type: "tool_use_start"
      call_id: string
      tool_name: string
      arguments: Record<string, unknown>
    }
  | {
      type: "tool_confirm_required"
      call_id: string
      tool_name: string
      arguments: Record<string, unknown>
    }
  | {
      type: "tool_use_result"
      call_id: string
      tool_name: string
      success: boolean
      output: unknown
      error: string | null
      duration_ms: number | null
    }
  | {
      type: "done"
      message_id: string
      iterations: number
      input_tokens: number
      output_tokens: number
      cache_creation_tokens: number
      cache_read_tokens: number
    }
  | { type: "error"; message: string; fatal: boolean }
