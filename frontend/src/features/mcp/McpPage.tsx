import { useEffect, useState } from "react"
import { mcpApi } from "./api"
import { McpServerForm } from "./McpServerForm"
import { McpServerList } from "./McpServerList"
import { NewMcpServerDialog } from "./NewMcpServerDialog"
import { QuickAddPanel } from "./QuickAddPanel"
import { CollapsibleSidebar } from "@/shared/CollapsibleSidebar"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { useTranslation } from "react-i18next"
import type { McpServer } from "./types"

export function McpPage() {
  const [servers, setServers] = useState<McpServer[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [showNew, setShowNew] = useState(false)
  // Anlegen/Ändern/Löschen/Verbinden erlaubt das Backend nur Admins
  // (api/routes/mcp.py). Nicht-Admins sehen die Server und können sie im
  // Agent-Editor ihren Agenten zuweisen (Task 692bd88d).
  const isAdmin = useAuthStore((s) => s.role) === "admin"
  const { t } = useTranslation("mcp")

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
    <div className="flex h-[calc(100dvh-3rem)] -m-4 md:-m-6">
      <main className="flex-1 min-w-0 overflow-y-auto">
        {active ? (
          <McpServerForm key={active.id} server={active} readOnly={!isAdmin}
            onSaved={handleSaved} onDeleted={handleDeleted} />
        ) : isAdmin ? (
          <div className="p-6">
            <QuickAddPanel
              existingIds={new Set(servers.map((s) => s.id))}
              onCreated={handleCreated}
            />
          </div>
        ) : (
          <p className="p-6 text-sm text-zinc-400">{t("admin_only_hint")}</p>
        )}
      </main>

      <CollapsibleSidebar>
        <McpServerList
          servers={servers} activeId={activeId}
          onSelect={setActiveId}
          onNew={isAdmin ? () => setShowNew(true) : undefined}
          onQuickAdd={isAdmin ? () => setActiveId(null) : undefined}
        />
      </CollapsibleSidebar>

      {isAdmin && showNew && <NewMcpServerDialog onClose={() => setShowNew(false)} onCreated={handleCreated} />}
    </div>
  )
}
