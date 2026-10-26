import { Navigate, useNavigate, useParams } from "react-router-dom"
import { SETTINGS_GROUPS } from "./registry"
import { ContentArea } from "./ContentArea"
import { legacyTarget } from "./legacyRedirects"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"

/**
 * „Meine Einstellungen“ (Benutzermenü/Zahnrad): persönliche Einstellungen als Reiter.
 * Kompakt nach docs/plans/meine-einstellungen-kompakt.md: Reiterleiste oben statt Spalten
 * links/rechts; der Inhalt nutzt die volle Breite. Alte Adressen von Admin-Gruppen leiten
 * ins Admin-Cockpit um (legacyRedirects.ts).
 */
export function SettingsHubPage() {
  const navigate = useNavigate()
  const { groupId } = useParams<{ groupId?: string }>()
  const redirect = legacyTarget(groupId)
  const active = SETTINGS_GROUPS.find((g) => g.id === groupId) ?? SETTINGS_GROUPS[0]

  if (redirect) return <Navigate to={redirect} replace />

  return (
    <CockpitShell title="Meine Einstellungen" className="cockpit-route flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]" hideHeader>
      <CockpitTopbar active="/settings" context="Deine persönlichen Einstellungen" />
      <main className="min-h-0 flex-1 overflow-hidden p-[10px]">
        <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-[4px] border border-[#2a364b] bg-[#0d1420]">
          <header className="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-2 border-b border-[#2a364b] bg-[#101724] px-3 py-2">
            <h1 className="text-sm font-black text-[#e8eef8]">Meine Einstellungen</h1>
            <div role="tablist" aria-label="Meine Einstellungen" className="flex min-w-0 basis-full gap-1 overflow-x-auto sm:basis-auto sm:flex-1">
              {SETTINGS_GROUPS.map((g) => {
                const Icon = g.icon
                const selected = g.id === active.id
                return (
                  <button key={g.id} type="button" role="tab" id={`settings-tab-${g.id}`}
                    aria-selected={selected} aria-controls="settings-pane"
                    onClick={() => navigate(`/settings/${g.id}`)}
                    className={`flex shrink-0 items-center gap-1.5 rounded-[3px] px-3 py-1.5 text-xs font-bold transition-colors sm:text-sm ${
                      selected ? "bg-[#1c2940] text-[#69d7ff]" : "text-[#8d9ab0] hover:bg-white/5 hover:text-[#e8eef8]"
                    }`}><Icon size={14} className="shrink-0" />{g.label}</button>
                )
              })}
            </div>
          </header>
          <section id="settings-pane" role="tabpanel" aria-labelledby={`settings-tab-${active.id}`} className="min-h-0 flex-1">
            <ContentArea key={active.id} group={active} />
          </section>
        </div>
      </main>
    </CockpitShell>
  )
}
