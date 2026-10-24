// Bereiche mit den für diesen Nutzer sichtbaren Apps, plus Anzeigename (docs/specs/startdesktop.md).
import { useMemo } from "react"
import { useTranslation } from "react-i18next"
import { Settings } from "lucide-react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { useMyAccess } from "@/features/access/useMyAccess"
import { visibleItems, type NavItem } from "@/shared/nav-config"
import { navLabel } from "@/shared/nav-label"
import { fillAreas } from "./areaLogic"

/** Der Einstellungs-Hub ist kein Menüeintrag, gehört aber in den Bereich Verwaltung. */
const SETTINGS_HUB: NavItem = { path: "/settings", icon: Settings, labelKey: "settings_hub", group: "settings", roles: ["admin"] }

export function useAreas() {
  const { t } = useTranslation("nav")
  const role = useAuthStore((s) => s.role)
  const access = useMyAccess()
  const areas = useMemo(
    () => fillAreas([...visibleItems(role, access), ...(role === "admin" ? [SETTINGS_HUB] : [])], role === "admin"),
    [role, access],
  )
  const label = (i: NavItem) => navLabel(t, i.labelKey, i.moduleId)
  return { areas, label }
}
