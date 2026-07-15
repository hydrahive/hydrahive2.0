import { useEffect, useState } from "react"
import { Plus, Server } from "lucide-react"
import { mcpApi } from "@/features/mcp/api"
import { McpServerForm } from "@/features/mcp/McpServerForm"
import { NewMcpServerDialog } from "@/features/mcp/NewMcpServerDialog"
import { QuickAddPanel } from "@/features/mcp/QuickAddPanel"
import type { McpServer } from "@/features/mcp/types"
import { CockpitButton } from "../CockpitButton"
import { AdminOverlay } from "./AdminOverlay"

export function McpOverlay({ onClose }: { onClose: () => void }) {
  const [servers, setServers] = useState<McpServer[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [showNew, setShowNew] = useState(false)

  async function loadServers(selectId?: string) {
    const list = await mcpApi.list()
    setServers(list)
    if (selectId) setActiveId(selectId)
    else if (!activeId && list.length > 0) setActiveId(list[0].id)
  }
  useEffect(() => { loadServers().catch(() => {}) }, [])

  function handleSaved(updated: McpServer) {
    setServers((cur) => cur.map((s) => (s.id === updated.id ? updated : s)))
  }
  function handleDeleted() {
    if (!activeId) return
    setServers((cur) => cur.filter((s) => s.id !== activeId))
    setActiveId(null)
  }
  function handleCreated(id: string) { setShowNew(false); loadServers(id) }

  const active = servers.find((s) => s.id === activeId) ?? null

  return (
    <AdminOverlay
      eyebrow="Admin"
      title="MCP-Server"
      onClose={onClose}
      maxWidthClass="max-w-5xl"
      headerActions={
        <CockpitButton tone="primary" onClick={() => setShowNew(true)}>
          <Plus size={12} className="mr-1 inline" />Neuer Server
        </CockpitButton>
      }
    >
      <div className="grid gap-4 md:grid-cols-[220px_1fr]">
        {/* Server-Liste */}
        <aside className="space-y-1.5">
          <button onClick={() => setActiveId(null)}
            className={`flex w-full items-center gap-2 rounded-[4px] border px-3 py-2 text-left text-xs font-medium transition-colors ${
              activeId === null ? "border-[#46617f] bg-[#172133] text-[#e8eef8]" : "border-[#2a364b] bg-[#111827] text-[#8d9ab0] hover:border-[#46617f] hover:text-[#e8eef8]"
            }`}>
            <Plus size={13} /> Schnell hinzufügen
          </button>
          {servers.length === 0 ? (
            <p className="py-6 text-center text-xs text-[#8d9ab0]">Noch keine Server.</p>
          ) : (
            servers.map((s) => (
              <button key={s.id} onClick={() => setActiveId(s.id)}
                className={`flex w-full items-start gap-2 rounded-[4px] border px-3 py-2 text-left transition-colors ${
                  s.id === activeId ? "border-[#46617f] bg-[#172133]" : "border-[#2a364b] bg-[#111827] hover:border-[#46617f]"
                }`}>
                <Server size={13} className="mt-0.5 shrink-0 text-[#69d7ff]" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-xs font-medium text-[#e8eef8]">{s.name || s.id}</span>
                  <span className="mt-0.5 block truncate font-mono text-[10px] text-[#5b6675]">{s.id}</span>
                </span>
              </button>
            ))
          )}
        </aside>

        {/* Detail: Form oder QuickAdd */}
        <main className="min-w-0">
          {active ? (
            <McpServerForm key={active.id} server={active} onSaved={handleSaved} onDeleted={handleDeleted} />
          ) : (
            <QuickAddPanel existingIds={new Set(servers.map((s) => s.id))} onCreated={handleCreated} />
          )}
        </main>
      </div>

      {showNew && <NewMcpServerDialog onClose={() => setShowNew(false)} onCreated={handleCreated} />}
    </AdminOverlay>
  )
}
