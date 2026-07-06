import { Link, Outlet } from "react-router-dom"
import { Grip, Settings } from "lucide-react"
import { AppFooter } from "@/shared/AppFooter"
import { AvatarMenu } from "@/shared/AvatarMenu"
import { DOMAIN_TW, colorFor } from "@/shared/colors"
import { navLabel } from "@/shared/nav-label"
import type { LayoutChrome } from "./types"

/** Test-Layout: Menü links in einer Seitenleiste, Inhalt rechts.
 *  Nutzt dieselben Nav-Daten wie das Standard-Layout — nur anders angeordnet.
 *  Beweist, dass ein Theme das komplette Layout umbaut, nicht nur Farben. */
export function SidebarLayout({ chrome }: { chrome: LayoutChrome }) {
  const { t, pathname, visible, currentPage, onBentoToggle, footer } = chrome

  return (
    <div className="flex h-[100dvh] overflow-hidden bg-[#0b0e16]">
      {/* Atmosphäre-Glow, dezenter am Rand */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -left-24 w-[520px] h-[440px] bg-violet-600/[14%] rounded-full blur-3xl" />
        <div className="absolute -bottom-44 -right-24 w-[520px] h-[440px] bg-teal-500/[12%] rounded-full blur-3xl" />
      </div>

      {/* Seitenleiste links */}
      <aside className="relative z-30 flex flex-col w-60 shrink-0 border-r border-white/[6%] bg-zinc-950/80 backdrop-blur">
        <div className="flex items-center gap-2 h-12 px-4 border-b border-white/[6%]">
          <Link to="/" className="flex items-center gap-2">
            <img
              src="/illustrations/logo-mark.png"
              alt=""
              className="w-8 h-8 object-contain drop-shadow-[0_0_8px_rgba(34,211,238,0.5)] select-none"
            />
            <span className="font-bold text-[var(--hh-accent-text)] tracking-tight">HydraHive</span>
          </Link>
        </div>

        <nav className="flex-1 overflow-y-auto p-2 space-y-0.5">
          {visible.map(({ path, icon: Icon, labelKey }) => {
            const active = path === "/" ? pathname === "/" : pathname.startsWith(path)
            const c = DOMAIN_TW[colorFor(path)]
            return (
              <Link
                key={path}
                to={path}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                  active ? `${c.bgActive} ${c.textActive}` : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[5%]"
                }`}
              >
                <Icon size={15} className="shrink-0" /> {navLabel(t, labelKey)}
              </Link>
            )
          })}
        </nav>

        <div className="flex items-center gap-1 p-2 border-t border-white/[6%]">
          <Link
            to="/settings"
            className={`p-1.5 rounded-md transition-colors ${
              pathname.startsWith("/settings")
                ? "text-violet-300 bg-violet-500/15"
                : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[5%]"
            }`}
            title={t("settings.gear_tooltip", { ns: "system", defaultValue: "Einstellungen" })}
          >
            <Settings size={16} />
          </Link>
          <button
            onClick={onBentoToggle}
            className="p-1.5 rounded-md text-zinc-400 hover:text-zinc-200 hover:bg-white/[5%]"
            title="Apps"
          >
            <Grip size={16} />
          </button>
          <div className="ml-auto">
            <AvatarMenu placement="top-left" />
          </div>
        </div>
      </aside>

      {/* Rechte Spalte: schmale Kopfzeile mit Breadcrumb + Content + Footer */}
      <div className="flex flex-col flex-1 min-w-0">
        <header className="relative z-20 flex items-center h-12 px-4 border-b border-white/[6%] bg-zinc-950/40 backdrop-blur">
          {currentPage && (
            <span className="flex items-center gap-1.5 text-sm text-zinc-300 truncate">
              <span className={`w-1.5 h-1.5 rounded-full ${DOMAIN_TW[colorFor(currentPage.path)].iconBgActive}`} />
              {navLabel(t, currentPage.labelKey)}
            </span>
          )}
        </header>

        <main className="flex-1 overflow-y-auto overflow-x-hidden overscroll-x-none relative z-10 p-4 md:p-6">
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
    </div>
  )
}
