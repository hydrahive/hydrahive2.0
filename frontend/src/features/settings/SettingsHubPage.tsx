import { Suspense, useEffect, useState } from "react"
import { Navigate, useParams, useNavigate } from "react-router-dom"
import { Loader2 } from "lucide-react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { SETTINGS_GROUPS, type SettingsGroup } from "./registry"
import { GroupList } from "./GroupList"
import { ContentArea } from "./ContentArea"
import { SubMenu } from "./SubMenu"
import { legacyTarget } from "./legacyRedirects"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"

/**
 * „Meine Einstellungen“ (unterm Zahnrad/Benutzermenü): nur persönliche Einstellungen.
 * Alte Adressen von Admin-Gruppen leiten ins Admin-Cockpit um (legacyRedirects.ts).
 * Ursprünglich die zentrale Einstellungsseite. 3-Spalten Master-Detail nach
 * Tills Blueprint-Board, im Werkbank-Look (blauer Rahmen #104E8B):
 *   links   = Hauptgruppen (Auswahl)
 *   mitte   = Inhalt mit Karteikarten-Tabs
 *   rechts  = kontextabhängiges Submenü (nur wenn group.hasSubmenu)
 */
export function SettingsHubPage() {
  const role = useAuthStore((s) => s.role) ?? "user"
  const navigate = useNavigate()
  const { groupId } = useParams<{ groupId?: string }>()
  const redirect = legacyTarget(groupId)
  const groups = SETTINGS_GROUPS.filter((g) => !g.adminOnly || role === "admin")

  // Aktive Gruppe aus der URL (/settings/:groupId), Fallback erste Gruppe.
  const active = groups.find((g) => g.id === groupId) ?? groups[0]
  const [subItem, setSubItem] = useState<string | null>(null)

  // Submenü-Auswahl zurücksetzen, wenn die Gruppe wechselt (auch via Deeplink).
  useEffect(() => { setSubItem(null) }, [active.id])

  const selectGroup = (g: SettingsGroup) => {
    navigate(`/settings/${g.id}`)
  }

  if (redirect) return <Navigate to={redirect} replace />

  return (
    <CockpitShell
      title="Meine Einstellungen"
      className="cockpit-route flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]"
      hideHeader
    >
      <CockpitTopbar active="/settings" context="Deine persönlichen Einstellungen" />
      <main className="min-h-0 flex-1 overflow-hidden p-[10px]">
        <div className="grid h-full min-h-0 overflow-hidden rounded-[4px] border border-[#2a364b] bg-[#101724] lg:grid-cols-[220px_minmax(0,1fr)_250px]">

        {/* Links: Hauptgruppen */}
        <div className="min-h-0 min-w-0 border-r border-[#2a364b] bg-[#101724]">
          <GroupList role={role} activeId={active.id} onSelect={selectGroup} />
        </div>

        {/* Mitte: Inhalt mit Tabs */}
        <div className="min-h-0 min-w-0 bg-[#0d1420]">
          <ContentArea group={active} subItem={subItem} />
        </div>

        {/* Rechts: Submenü — nur wenn die Gruppe eins braucht. Eigene
            submenuComponent (z.B. Agentenliste mit Farben) hat Vorrang. */}
        {active.hasSubmenu && (() => {
          const Custom = active.submenuComponent
          return (
            <div className="min-h-0 min-w-0 border-l border-[#2a364b] bg-[#101724]">
              {Custom ? (
                <Suspense fallback={
                  <div className="flex h-full items-center justify-center">
                    <Loader2 size={18} className="animate-spin text-zinc-500" />
                  </div>
                }>
                  <Custom activeItem={subItem} onSelect={setSubItem} />
                </Suspense>
              ) : (
                <SubMenu group={active} activeItem={subItem} onSelect={setSubItem} />
              )}
            </div>
          )
        })()}
        </div>
      </main>
    </CockpitShell>
  )
}
