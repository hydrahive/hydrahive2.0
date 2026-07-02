import { Link, useLocation } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { DOMAIN_TW, colorFor } from "@/shared/colors"
import { navLabel } from "@/shared/nav-label"
import { visibleItems } from "@/shared/nav-config"

/** Navigations-Baustein für Templates.
 *    <hh-menu type="horizontal"/>  (Default)
 *    <hh-menu type="vertical"/>
 *
 *  Nutzt dieselbe rollen-gefilterte Nav-Config wie die eingebauten Layouts —
 *  ein Designer platziert das Menü frei, Inhalt/Rechte bleiben konsistent. */
export function MenuBlock({ attrs }: { attrs: Record<string, string> }) {
  const vertical = attrs.type === "vertical"
  const role = useAuthStore((s) => s.role)
  const { t } = useTranslation("nav")
  const { pathname } = useLocation()
  const items = visibleItems(role)

  return (
    <nav className={vertical ? "flex flex-col gap-0.5" : "flex flex-wrap items-center gap-1"}>
      {items.map(({ path, icon: Icon, labelKey }) => {
        const active = path === "/" ? pathname === "/" : pathname.startsWith(path)
        const c = DOMAIN_TW[colorFor(path)]
        return (
          <Link
            key={path}
            to={path}
            className={`flex items-center gap-2 rounded-lg text-sm transition-colors ${
              vertical ? "px-3 py-2" : "px-2.5 py-1.5"
            } ${active ? `${c.bgActive} ${c.textActive}` : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[6%]"}`}
          >
            <Icon size={15} className="shrink-0" /> {navLabel(t, labelKey)}
          </Link>
        )
      })}
    </nav>
  )
}
