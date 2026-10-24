// VORSCHAU Startdesktop: Bereiche mit den für diesen Nutzer sichtbaren Apps, plus Anzeigenamen.
import { useMemo } from "react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { useMyAccess } from "@/features/access/useMyAccess"
import { visibleItems, type NavItem } from "@/shared/nav-config"
import { navLabel } from "@/shared/nav-label"
import { LABELS } from "./groups"
import { EXTRA_ITEMS, fillGroups } from "./startLogic"

export function useAreas() {
  const { t } = useTranslation("nav")
  const role = useAuthStore((s) => s.role)
  const access = useMyAccess()
  const groups = useMemo(
    () => fillGroups([...visibleItems(role, access), ...(role === "admin" ? EXTRA_ITEMS : [])], role === "admin"),
    [role, access],
  )
  const label = (i: NavItem) => LABELS[i.path] ?? navLabel(t, i.labelKey)
  return { groups, label }
}
