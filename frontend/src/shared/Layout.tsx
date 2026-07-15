import { useEffect, useState } from "react"
import { Outlet, useLocation } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { UpdateModal } from "@/shared/UpdateModal"
import { AppFooter } from "@/shared/AppFooter"
import { useLayoutUpdate } from "./useLayoutUpdate"
import { BentoMenu } from "./BentoMenu"
import { COCKPIT_MODULE_ITEMS, NAV_ITEMS, QUICK_LINK_PATHS, visibleItems } from "./nav-config"
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
    version, commit, updateBehind, moduleUpdateCount,
    updateState, updateError, newCommit,
    confirmUpdate, openUpdateModal, closeUpdateModal,
  } = useLayoutUpdate(role === "admin")
  const [bentoOpen, setBentoOpen] = useState(false)

  // Aktives Theme (aus localStorage). Re-render bei Wechsel via Custom-Event.
  const [themeId, setThemeId] = useState(getStoredThemeId)
  useEffect(() => {
    const onChange = () => setThemeId(getStoredThemeId())
    window.addEventListener("hh-theme-change", onChange)
    return () => window.removeEventListener("hh-theme-change", onChange)
  }, [])

  const theme = getTheme(themeId)
  // Core-Cockpits + installierte Cockpit-Module (nav mit cockpit:true) laufen
  // im bare Cockpit-Chrome statt im Theme-Layout.
  const cockpitPaths = ["/projects", "/buddy", "/media", "/vault", "/admin",
    ...COCKPIT_MODULE_ITEMS.map((i) => i.path)]
  const isCockpitRoute = cockpitPaths.some((path) => pathname === path || pathname.startsWith(`${path}/`))

  // Theme-CSS-Variablen auf <html> anwenden (überschreibt --hh-*).
  useEffect(() => {
    const el = document.documentElement
    const vars = theme.variables ?? {}
    for (const [k, v] of Object.entries(vars)) el.style.setProperty(k, v)
    return () => {
      for (const k of Object.keys(vars)) el.style.removeProperty(k)
    }
  }, [theme])

  // Optionales rohes Theme-CSS (aus theme.css eines Pakets) einhängen.
  useEffect(() => {
    if (!theme.css) return
    const style = document.createElement("style")
    style.setAttribute("data-hh-theme", theme.id)
    style.textContent = theme.css
    document.head.appendChild(style)
    return () => {
      style.remove()
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
      version, commit, updateBehind, moduleUpdateCount,
      isAdmin: role === "admin",
      onUpdateClick: openUpdateModal,
    },
  }

  const ActiveLayout = theme.layout

  return (
    <>
      {isCockpitRoute ? (
        <div className="flex h-[100dvh] min-h-0 flex-col bg-[#080b11]">
          <main className="min-h-0 flex-1 overflow-hidden">
            <Outlet />
          </main>
          <AppFooter
            version={version}
            commit={commit}
            updateBehind={updateBehind}
            moduleUpdateCount={moduleUpdateCount}
            isAdmin={role === "admin"}
            onUpdateClick={openUpdateModal}
          />
        </div>
      ) : (
        <ActiveLayout chrome={chrome} />
      )}

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
