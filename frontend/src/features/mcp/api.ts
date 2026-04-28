import { api } from "@/shared/api-client"
import type { McpServer, McpServerCreate, McpTool } from "./types"

export interface QuickAddTemplate {
  id: string
  name: string
  description: string
  transport: string
  command: string
  args: string[]
  env: Record<string, string>
  user_inputs: { key: string; label: string; default: string; required: boolean; secret?: boolean }[]
}

export const mcpApi = {
  list: () => api.get<McpServer[]>("/mcp/servers"),
  get: (id: string) => api.get<McpServer>(`/mcp/servers/${id}`),
  create: (req: McpServerCreate) => api.post<McpServer>("/mcp/servers", req),
  update: (id: string, fields: Partial<McpServerCreate>) =>
    api.patch<McpServer>(`/mcp/servers/${id}`, fields),
  delete: (id: string) => api.delete<void>(`/mcp/servers/${id}`),
  connect: (id: string) =>
    api.post<{ connected: boolean; tools: McpTool[] }>(`/mcp/servers/${id}/connect`, {}),
  disconnect: (id: string) =>
    api.post<{ disconnected: boolean }>(`/mcp/servers/${id}/disconnect`, {}),
  tools: (id: string) => api.get<McpTool[]>(`/mcp/servers/${id}/tools`),
  quickAddTemplates: () => api.get<QuickAddTemplate[]>("/mcp/quick-add"),
  quickAdd: (template_id: string, server_id: string, inputs: Record<string, string>) =>
    api.post<McpServer>("/mcp/quick-add", { template_id, server_id, inputs }),
}
