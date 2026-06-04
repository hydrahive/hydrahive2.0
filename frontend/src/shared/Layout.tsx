import { useState } from "react"
import { Link, Outlet, useLocation } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { Grip } from "lucide-react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { UpdateModal } from "@/shared/UpdateModal"
import { useLayoutUpdate } from "./useLayoutUpdate"
import { AppFooter } from "./AppFooter"
import { AvatarMenu } from "./AvatarMenu"
import { BentoMenu } from "./BentoMenu"
import { DOMAIN_TW, colorFor } from "./colors"
import { NAV_ITEMS, QUICK_LINK_PATHS, visibleItems } from "./nav-config"
import { navLabel } from "./nav-label"

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

  const visible = visibleItems(role)
  const quickLinks = QUICK_LINK_PATHS
    .map((p) => visible.find((i) => i.path === p))
    .filter(Boolean) as typeof NAV_ITEMS
  const currentPage = visible.find((i) =>
    i.path === "/" ? pathname === "/" : pathname.startsWith(i.path)
  )

  return (
    <div className="flex flex-col h-[100dvh] overflow-hidden bg-[#0b0e16]">
      {/* Atmosphäre-Glows (Redesign): violett oben-mitte, teal unten-links, amber unten-rechts */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[560px] h-[400px] bg-violet-600/[18%] rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-24 w-[520px] h-[440px] bg-teal-500/[15%] rounded-full blur-3xl" />
        <div className="absolute -bottom-44 -right-24 w-[520px] h-[440px] bg-amber-500/[14%] rounded-full blur-3xl" />
      </div>

      {/* Top-Bar */}
      <header className="relative z-30 flex items-center gap-2 px-3 sm:px-4 h-12 border-b border-white/[6%] bg-zinc-950/80 backdrop-blur">
        <Link to="/" className="flex items-center gap-2 shrink-0">
          <img
            src="/illustrations/logo-mark.png"
            alt=""
            className="w-8 h-8 object-contain drop-shadow-[0_0_8px_rgba(34,211,238,0.5)] select-none"
          />
          <span className="hidden sm:inline font-bold text-[var(--hh-accent-text)] tracking-tight">
            HydraHive
          </span>
        </Link>

        {currentPage && (
          <span className="flex items-center gap-1.5 text-[11px] sm:text-sm text-zinc-400 ml-1 sm:ml-2 truncate">
            <span className="text-zinc-600 mx-1">/</span>
            <span className={`w-1.5 h-1.5 rounded-full ${DOMAIN_TW[colorFor(currentPage.path)].iconBgActive}`} />
            {navLabel(t, currentPage.labelKey)}
          </span>
        )}

        <div className="flex-1" />

        <nav className="hidden lg:flex items-center gap-1">
          {quickLinks.map(({ path, icon: Icon, labelKey }) => {
            const active = path === "/" ? pathname === "/" : pathname.startsWith(path)
            const c = DOMAIN_TW[colorFor(path)]
            return (
              <Link
                key={path}
                to={path}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs transition-colors ${
                  active
                    ? `${c.bgActive} ${c.textActive}`
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[5%]"
                }`}
              >
                <Icon size={13} /> {navLabel(t, labelKey)}
              </Link>
            )
          })}
        </nav>

        <button
          onClick={() => setBentoOpen((o) => !o)}
          className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-200 hover:bg-white/[5%]"
          title="Apps"
        >
          <Grip size={16} />
        </button>

        <AvatarMenu />
      </header>

      <BentoMenu open={bentoOpen} onClose={() => setBentoOpen(false)} />

      {/* Content — overflow-x-hidden + overscroll-x-none: kein horizontales Pannen
          auf Touch-Geräten (sonst wischt der Chat „ins Nirvana"). Vertikal scrollt
          weiter; breite Inhalte (Code/Tabellen/Monaco) haben eigene innere Scroller. */}
      <main className="flex-1 overflow-y-auto overflow-x-hidden overscroll-x-none relative z-10 p-4 md:p-6">
        <Outlet />
      </main>

      <AppFooter
        version={version} commit={commit} updateBehind={updateBehind}
        isAdmin={role === "admin"}
        onUpdateClick={openUpdateModal}
      />

      {updateState !== "idle" && (
        <UpdateModal
          state={updateState} newCommit={newCommit} errorMessage={updateError}
          forceMode={updateBehind === 0}
          onConfirm={confirmUpdate} onClose={closeUpdateModal}
        />
      )}
    </div>
  )
}
