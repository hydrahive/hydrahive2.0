import { CockpitPanel } from "./CockpitPanel"
import { CockpitShell } from "./CockpitShell"
import { CockpitTopbar } from "./CockpitTopbar"
import { explicitAiActions, openLocalPath } from "./actionRegistry"
import { AccessNotice } from "@/features/access/AccessNotice"
import { TileIcon } from "@/shared/brand/TileIcon"
import { AdminHealthPanel } from "./admin/AdminHealthPanel"
import { AdminOverlays } from "./admin/AdminOverlays"
import { OVERLAY_BY_ACTION, OVERLAY_BY_PATH } from "./admin/adminOverlayRegistry"
import { useAdminOverlayNavigation } from "./admin/useAdminOverlayNavigation"
import { ADMIN_AREAS, OPS_LINKS, type AdminLink } from "./adminCockpitLinks"

/**
 * Admin-Startseite (Plan admin-cockpit-kompakt): drei Kästen, jeder Einstieg genau einmal.
 * Verwaltung links, Betrieb in der Mitte, echter Zustand rechts – keine Erklär- und Roadmap-Kästen mehr.
 */
export function AdminCockpitPage() {
  const { overlay, selectedContainerId, setOverlay, setContainerDetail } = useAdminOverlayNavigation()

  const open = (link: AdminLink) => {
    const target = (link.id ? OVERLAY_BY_ACTION[link.id] : undefined) ?? OVERLAY_BY_PATH[link.path]
    if (target) setOverlay(target)
    else openLocalPath(link.path)
  }
  const openAgent = () => openLocalPath(explicitAiActions.find((a) => a.id === "admin-agent")?.path ?? "/buddy")

  return (
    <CockpitShell eyebrow="Admin" title="Admin-Cockpit" className="flex h-full min-h-0 flex-col overflow-hidden bg-s-grund" hideHeader>
      <CockpitTopbar active="admin" context="Admin" />
      <div className="grid min-h-0 flex-1 gap-[10px] overflow-y-auto p-[10px] lg:grid-cols-[280px_minmax(0,1fr)] xl:grid-cols-[280px_minmax(0,1fr)_340px] xl:overflow-hidden">
        <aside className="xl:min-h-0 xl:overflow-y-auto">
          <CockpitPanel theme="status" title="Verwaltung" eyebrow="Admin">
            <div className="space-y-1.5">
              {ADMIN_AREAS.map((item) => (
                <button key={item.path} type="button" onClick={() => open(item)}
                  className="group flex w-full items-center gap-3 rounded-[4px] border border-s-rand bg-s-innen p-2 text-left transition-colors hover:border-s-rand-hover hover:bg-s-hebung">
                  <TileIcon target={item.path} icon={item.icon} />
                  <span className="min-w-0">
                    <span className="block text-sm font-bold text-[#e8eef8]">{item.title}</span>
                    <span className="block truncate text-xs text-[#9aa7bc]">{item.desc}</span>
                  </span>
                </button>
              ))}
            </div>
          </CockpitPanel>
        </aside>

        <main className="space-y-[10px] xl:min-h-0 xl:overflow-y-auto">
          <AccessNotice onOpen={() => setOverlay("access")} />
          <CockpitPanel theme="werkzeug" title="Betriebszentrale" eyebrow="Betrieb">
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
              {OPS_LINKS.map((item) => (
                <button key={item.path} type="button" onClick={() => open(item)}
                  className="group flex items-center gap-2.5 rounded-[4px] border border-s-rand bg-s-innen p-2 text-left hover:border-s-rand-hover hover:bg-s-hebung">
                  <TileIcon target={item.path} icon={item.icon} />
                  <span className="min-w-0 text-sm font-bold leading-tight text-[#e8eef8]">{item.title}</span>
                </button>
              ))}
            </div>
          </CockpitPanel>
        </main>

        <aside className="lg:col-span-2 xl:col-span-1 xl:min-h-0 xl:overflow-y-auto">
          <AdminHealthPanel onOpenSystem={() => setOverlay("system")} onOpenAgent={openAgent} />
        </aside>
      </div>

      <AdminOverlays overlay={overlay} selectedContainerId={selectedContainerId}
        onClose={() => setOverlay(null)} onSelectContainer={setContainerDetail} />
    </CockpitShell>
  )
}
