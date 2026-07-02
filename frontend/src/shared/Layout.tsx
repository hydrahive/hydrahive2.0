import { useEffect, useState } from "react"
import { useLocation } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { UpdateModal } from "@/shared/UpdateModal"
import { useLayoutUpdate } from "./useLayoutUpdate"
import { BentoMenu } from "./BentoMenu"
import { NAV_ITEMS, QUICK_LINK_PATHS, visibleItems } from "./nav-config"
import { getStoredThemeId, getTheme } from "./themes/registry"
import type { LayoutChrome } from "./layouts/types"

/** LayoutHost — sammelt gemeinsames Chrome (Nav, Update-State), wählt das aktive
 *  Theme-Layout-Gerüst und hält globale Overlays (Bento, UpdateModal). Das
 *  eigentliche Gerüst (Menü oben / Sidebar / …) liefert das Theme. */
export function Layout() {
  const { role } = useAuthStore()
  const { t } = useTranslation("nav")
  const { pathname } = useLocation()

  const {
    version, commit, updateBehind,
    updateState, updateError, newCommit,
    confirmUpdate, openUpdateModal, closeUpdateModal,
  } = useLayoutUpdate()
  const [bentoOpen, setBentoOpen] = useState(false)

  // Aktives Theme (aus localStorage). Re-render bei Wechsel via Custom-Event.
  const [themeId, setThemeId] = useState(getStoredThemeId)
  useEffect(() => {
    const onChange = () => setThemeId(getStoredThemeId())
    window.addEventListener("hh-theme-change", onChange)
    return () => window.removeEventListener("hh-theme-change", onChange)
  }, [])

  const theme = getTheme(themeId)

  // Theme-CSS-Variablen auf <html> anwenden (überschreibt --hh-*).
  useEffect(() => {
    const el = document.documentElement
    const vars = theme.variables ?? {}
    for (const [k, v] of Object.entries(vars)) el.style.setProperty(k, v)
    return () => {
      for (const k of Object.keys(vars)) el.style.removeProperty(k)
    }
  }, [theme])

  const visible = visibleItems(role)
  const quickLinks = QUICK_LINK_PATHS
    .map((p) => visible.find((i) => i.path === p))
    .filter(Boolean) as typeof NAV_ITEMS
  const currentPage = visible.find((i) =>
    i.path === "/" ? pathname === "/" : pathname.startsWith(i.path),
  )

  const chrome: LayoutChrome = {
    role, t, pathname, visible, quickLinks, currentPage,
    onBentoToggle: () => setBentoOpen((o) => !o),
    footer: {
      version, commit, updateBehind,
      isAdmin: role === "admin",
      onUpdateClick: openUpdateModal,
    },
  }

  const ActiveLayout = theme.layout

  return (
    <>
      <ActiveLayout chrome={chrome} />

      <BentoMenu open={bentoOpen} onClose={() => setBentoOpen(false)} />

      {updateState !== "idle" && (
        <UpdateModal
          state={updateState} newCommit={newCommit} errorMessage={updateError}
          forceMode={updateBehind === 0}
          onConfirm={confirmUpdate} onClose={closeUpdateModal}
        />
      )}
    </>
  )
}
