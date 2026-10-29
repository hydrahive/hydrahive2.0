import { useLocation } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { UpdateModal } from "@/shared/UpdateModal"
import { VaultPinDialog } from "@/features/vault/VaultPinDialog"
import { StaleBundleBanner } from "@/shared/StaleBundleBanner"
import { AppFooter } from "@/shared/AppFooter"
import { useLayoutUpdate } from "./useLayoutUpdate"
import { cockpitModuleItems, visibleItems } from "./nav-config"
import { navLabel } from "./nav-label"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { AccessOutlet } from "@/features/access/AccessOutlet"
import { useMyAccess } from "@/features/access/useMyAccess"
import { HelpAssistant } from "@/features/helpdesk/HelpAssistant"

/** LayoutHost — sammelt gemeinsames Chrome (Nav, Update-State) und hält globale
 *  Overlays (Bento, UpdateModal). Es gibt nur ein Design: Cockpits laufen im
 *  bloßen Cockpit-Rahmen, alle anderen Seiten mit Cockpit-Kopfzeile. */
export function Layout() {
  const { role } = useAuthStore()
  const { t } = useTranslation("nav")
  const { pathname } = useLocation()

  const {
    version, commit, updateBehind, moduleUpdateCount, pluginUpdateCount, stale,
    updateState, updateError, newCommit,
    confirmUpdate, openUpdateModal, closeUpdateModal,
  } = useLayoutUpdate(role === "admin")

  // Core-Cockpits + installierte Cockpit-Module (nav mit cockpit:true) laufen
  // im bloßen Cockpit-Rahmen, alle anderen Seiten mit Cockpit-Kopfzeile.
  const cockpitPaths = ["/start", "/projects", "/buddy", "/media", "/vault", "/admin", "/werkstatt", "/help", "/settings",
    ...cockpitModuleItems().map((i) => i.path)]
  const isCockpitRoute = cockpitPaths.some((path) => pathname === path || pathname.startsWith(`${path}/`))

  const access = useMyAccess()
  const visible = visibleItems(role, access)
  const currentPage = visible.find((i) =>
    i.path === "/" ? pathname === "/" : pathname.startsWith(i.path),
  )

  return (
    <>
      {isCockpitRoute ? (
        <div className="flex h-[100dvh] min-h-0 flex-col bg-[#080b11]">
          {stale && <StaleBundleBanner />}
          <main className="min-h-0 flex-1 overflow-hidden">
            <AccessOutlet />
          </main>
          <AppFooter
            version={version}
            commit={commit}
            updateBehind={updateBehind}
            moduleUpdateCount={moduleUpdateCount}
            pluginUpdateCount={pluginUpdateCount}
            isAdmin={role === "admin"}
            onUpdateClick={openUpdateModal}
          />
        </div>
      ) : (
        <div className="cockpit-route flex h-[100dvh] min-h-0 flex-col bg-[#080b11]">
          {stale && <StaleBundleBanner />}
          <CockpitTopbar
            active={pathname}
            context={currentPage ? navLabel(t, currentPage.labelKey) : undefined}
          />
          <main className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden overscroll-x-none p-4 md:p-6">
            <AccessOutlet />
          </main>
          <AppFooter
            version={version}
            commit={commit}
            updateBehind={updateBehind}
            moduleUpdateCount={moduleUpdateCount}
            pluginUpdateCount={pluginUpdateCount}
            isAdmin={role === "admin"}
            onUpdateClick={openUpdateModal}
          />
        </div>
      )}

      <VaultPinDialog />
      <HelpAssistant />
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
