import { useEffect, useState } from "react"
import { mcpApi } from "./api"
import { McpServerForm } from "./McpServerForm"
import { McpServerList } from "./McpServerList"
import { NewMcpServerDialog } from "./NewMcpServerDialog"
import { QuickAddPanel } from "./QuickAddPanel"
import type { McpServer } from "./types"

export function McpPage() {
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

  function handleCreated(id: string) {
    setShowNew(false)
    loadServers(id)
  }

  const active = servers.find((s) => s.id === activeId) ?? null

  return (
    <div className="flex h-[calc(100vh-3.5rem)] -m-6">
      <main className="flex-1 min-w-0 overflow-y-auto">
        {active ? (
          <McpServerForm key={active.id} server={active} onSaved={handleSaved} onDeleted={handleDeleted} />
        ) : (
          <div className="p-6">
            <QuickAddPanel
              existingIds={new Set(servers.map((s) => s.id))}
              onCreated={handleCreated}
            />
          </div>
        )}
      </main>

      <aside className="w-72 border-l border-white/[6%] bg-white/[2%] flex-shrink-0">
        <McpServerList
          servers={servers} activeId={activeId}
          onSelect={setActiveId}
          onNew={() => setShowNew(true)}
          onQuickAdd={() => setActiveId(null)}
        />
      </aside>

      {showNew && <NewMcpServerDialog onClose={() => setShowNew(false)} onCreated={handleCreated} />}
    </div>
  )
}
