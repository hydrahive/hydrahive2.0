export interface McpServer {
  id: string
  name: string
  transport: "stdio" | "http" | "sse"
  description: string
  enabled: boolean
  connected: boolean
  command?: string
  args?: string[]
  env?: Record<string, string>
  url?: string
  headers?: Record<string, string>
  created_at: string
  updated_at: string
}

export interface McpTool {
  name: string
  description: string
  schema: Record<string, unknown>
}

export interface McpServerCreate {
  id: string
  name: string
  transport: "stdio" | "http" | "sse"
  description: string
  enabled: boolean
  command?: string
  args?: string[]
  env?: Record<string, string>
  url?: string
  headers?: Record<string, string>
}
