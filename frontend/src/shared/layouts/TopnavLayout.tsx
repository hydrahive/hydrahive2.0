import { Link, Outlet } from "react-router-dom"
import { Grip, Settings } from "lucide-react"
import { AppFooter } from "@/shared/AppFooter"
import { AvatarMenu } from "@/shared/AvatarMenu"
import { DOMAIN_TW, colorFor } from "@/shared/colors"
import { navLabel } from "@/shared/nav-label"
import type { LayoutChrome } from "./types"

/** Standard-Layout: Menü oben für Legacy-Routen mit Cockpit-Topbar-Chrome. */
export function TopnavLayout({ chrome }: { chrome: LayoutChrome }) {
  const { t, pathname, quickLinks, currentPage, onBentoToggle, footer } = chrome

  return (
    <div className="flex flex-col h-[100dvh] overflow-hidden bg-[#0b0e16]">
      {/* Atmosphäre-Glows: violett oben-mitte, teal unten-links, amber unten-rechts */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 left-1/2 -translate-x-1/2 w-[560px] h-[400px] bg-violet-600/[18%] rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-24 w-[520px] h-[440px] bg-teal-500/[15%] rounded-full blur-3xl" />
        <div className="absolute -bottom-44 -right-24 w-[520px] h-[440px] bg-amber-500/[14%] rounded-full blur-3xl" />
      </div>

      {/* Globale Topbar: gleiche Formensprache wie das Cockpit-Chrome. */}
      <header className="relative z-30 flex h-[58px] min-w-0 items-center gap-3 border-b border-[#2a364b] bg-gradient-to-b from-[#131b2a] to-[#0e1420] px-3 sm:px-[18px]">
        <Link to="/" className="flex items-center gap-2 shrink-0">
          <img
            src="/illustrations/logo-mark.png"
            alt=""
            className="w-8 h-8 object-contain drop-shadow-[0_0_8px_rgba(34,211,238,0.5)] select-none"
          />
          <span className="hidden font-black tracking-[-0.03em] text-[#e8eef8] sm:inline">
            HydraHive
          </span>
        </Link>

        {currentPage && (
          <span className="min-w-0 truncate text-[11px] text-[#8d9ab0] sm:text-sm">
            <span className="mx-1 text-[#68758a] sm:mx-2">/</span>
            <span className={`mr-1.5 inline-block h-1.5 w-1.5 rounded-full ${DOMAIN_TW[colorFor(currentPage.path)].iconBgActive}`} />
            {navLabel(t, currentPage.labelKey)}
          </span>
        )}

        <div className="min-w-0 flex-1" />

        <nav className="hidden lg:flex items-center gap-1">
          {quickLinks.map(({ path, icon: Icon, labelKey }) => {
            const active = path === "/" ? pathname === "/" : pathname.startsWith(path)
            return (
              <Link
                key={path}
                to={path}
                className={`flex items-center gap-1.5 rounded-[4px] px-3 py-2 text-xs transition-colors ${
                  active ? "bg-[#1c2940] font-semibold text-[#69d7ff]" : "text-[#8d9ab0] hover:bg-white/[6%] hover:text-[#e8eef8]"
                }`}
              >
                <Icon size={13} /> {navLabel(t, labelKey)}
              </Link>
            )
          })}
        </nav>

        <Link
          to="/settings"
          className={`rounded-[4px] border p-2 transition-colors ${
            pathname.startsWith("/settings")
              ? "border-[#69d7ff]/35 bg-[#1c2940] text-[#69d7ff]"
              : "border-[#2a364b] bg-[#172133] text-[#8d9ab0] hover:border-[#46617f] hover:text-[#e8eef8]"
          }`}
          title={t("settings.gear_tooltip", { ns: "system", defaultValue: "Einstellungen" })}
        >
          <Settings size={16} />
        </Link>

        <button
          onClick={onBentoToggle}
          className="rounded-[4px] border border-[#2a364b] bg-[#172133] p-2 text-[#8d9ab0] hover:border-[#46617f] hover:text-[#e8eef8]"
          title="Apps"
        >
          <Grip size={16} />
        </button>

        <AvatarMenu />
      </header>

      {/* Content — overflow-x-hidden + overscroll-x-none: kein horizontales Pannen
          auf Touch-Geräten. Vertikal scrollt weiter. */}
      <main className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden overscroll-x-none relative z-10 p-4 md:p-6">
        <Outlet />
      </main>

      <AppFooter
        version={footer.version}
        commit={footer.commit}
        updateBehind={footer.updateBehind}
        moduleUpdateCount={footer.moduleUpdateCount}
        isAdmin={footer.isAdmin}
        onUpdateClick={footer.onUpdateClick}
      />
    </div>
  )
}
