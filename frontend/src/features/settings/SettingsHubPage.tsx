import { useState } from "react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { SETTINGS_GROUPS, type SettingsGroup } from "./registry"
import { GroupList } from "./GroupList"
import { ContentArea } from "./ContentArea"
import { SubMenu } from "./SubMenu"

/**
 * Zentrale Einstellungsseite (unterm Zahnrad). 3-Spalten Master-Detail nach
 * Tills Blueprint-Board, im Werkbank-Look (blauer Rahmen #104E8B):
 *   links   = Hauptgruppen (Auswahl)
 *   mitte   = Inhalt mit Karteikarten-Tabs
 *   rechts  = kontextabhängiges Submenü (nur wenn group.hasSubmenu)
 */
export function SettingsHubPage() {
  const role = useAuthStore((s) => s.role) ?? "user"
  const groups = SETTINGS_GROUPS.filter((g) => !g.adminOnly || role === "admin")
  const [active, setActive] = useState<SettingsGroup>(groups[0])
  const [subItem, setSubItem] = useState<string | null>(null)

  const selectGroup = (g: SettingsGroup) => {
    setActive(g)
    setSubItem(null)
  }

  return (
    <div className="flex flex-col p-3 md:p-4 h-full">
      <div
        className="relative flex flex-1 overflow-hidden rounded-[28px] border border-[#104E8B]/70 shadow-2xl shadow-[0_0_50px_-12px_rgba(16,78,139,0.6)] backdrop-blur"
      >
        <div className="pointer-events-none absolute inset-0 rounded-[28px] ring-1 ring-inset ring-[#104E8B]/30" />

        {/* Links: Hauptgruppen */}
        <div className="w-56 shrink-0 border-r border-white/8 bg-zinc-950/50">
          <GroupList role={role} activeId={active.id} onSelect={selectGroup} />
        </div>

        {/* Mitte: Inhalt mit Tabs */}
        <div className="flex-1 min-w-0 bg-zinc-950/20">
          <ContentArea group={active} subItem={subItem} />
        </div>

        {/* Rechts: Submenü — nur wenn die Gruppe eins braucht */}
        {active.hasSubmenu && (
          <div className="w-56 shrink-0 border-l border-white/8 bg-zinc-950/50">
            <SubMenu group={active} activeItem={subItem} onSelect={setSubItem} />
          </div>
        )}
      </div>
    </div>
  )
}
