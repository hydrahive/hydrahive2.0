export type AdminOverlayId = "users" | "modules" | "plugins" | "credentials" | "themes" | "mcp" | "llm" | "extensions" | "system" | "system-settings" | "containers" | "vms" | "nodes" | "jobs"

const ADMIN_OVERLAY_IDS = new Set<AdminOverlayId>([
  "users", "modules", "plugins", "credentials", "themes", "mcp", "llm",
  "extensions", "system", "system-settings", "containers", "vms", "nodes", "jobs",
])

export function isAdminOverlayId(value: string | null): value is AdminOverlayId {
  return value !== null && ADMIN_OVERLAY_IDS.has(value as AdminOverlayId)
}

export const OVERLAY_BY_ACTION: Record<string, AdminOverlayId> = {
  users: "users", modules: "modules", plugins: "plugins", credentials: "credentials",
  extensions: "extensions", system: "system",
}

export const OVERLAY_BY_PATH: Record<string, AdminOverlayId> = {
  "/modules": "modules", "/plugins": "plugins", "/credentials": "credentials",
  "/themes": "themes", "/mcp": "mcp", "/llm": "llm", "/extensions": "extensions",
  "/system": "system", "/system/settings": "system-settings", "/containers": "containers",
  "/vms": "vms", "/nodes": "nodes", "/jobs": "jobs",
}
