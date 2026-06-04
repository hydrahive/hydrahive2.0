import { useTranslation } from "react-i18next"
import { NavLink } from "react-router-dom"

export function AkteSidebar() {
  const { t } = useTranslation("akte")

  const sections = [
    {
      title: t("nav.section_akte"),
      items: [
        { to: "/akte/uebersicht",     icon: "🗂", label: t("nav.overview") },
        { to: "/akte/timeline",       icon: "📅", label: t("nav.timeline") },
        { to: "/akte/conditions",     icon: "🔴", label: t("nav.conditions") },
        { to: "/akte/medications",    icon: "💊", label: t("nav.medications") },
        { to: "/akte/observations",   icon: "🧪", label: t("nav.observations") },
        { to: "/akte/allergies",      icon: "🤧", label: t("nav.allergies") },
        { to: "/akte/events",         icon: "📋", label: t("nav.events") },
        { to: "/akte/imaging",        icon: "🩻", label: t("nav.imaging") },
        { to: "/akte/practitioners",  icon: "👨‍⚕️", label: t("nav.practitioners") },
        { to: "/akte/documents",      icon: "📄", label: t("nav.documents") },
        { to: "/akte/notes",          icon: "📝", label: t("nav.notes") },
      ],
    },
    {
      title: t("nav.section_import"),
      items: [
        { to: "/akte/import", icon: "📥", label: t("nav.import") },
      ],
    },
    {
      title: t("nav.section_tracking"),
      items: [
        { to: "/akte/tracking", icon: "🍎", label: t("nav.tracking") },
        { to: "/akte/schlaf",   icon: "😴", label: t("nav.sleep") },
      ],
    },
  ]

  return (
    <nav className="w-48 flex-shrink-0 flex flex-col gap-4 py-2">
      {sections.map((section) => (
        <div key={section.title}>
          <p className="px-3 mb-1 text-[10px] font-bold uppercase tracking-widest text-zinc-600">
            {section.title}
          </p>
          {section.items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors ${
                  isActive
                    ? "bg-rose-500/10 text-rose-300 border-l-2 border-rose-500"
                    : "text-zinc-500 hover:text-zinc-300 hover:bg-white/[4%] border-l-2 border-transparent"
                }`
              }
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </div>
      ))}
    </nav>
  )
}
