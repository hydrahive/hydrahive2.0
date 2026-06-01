import { useTranslation } from "react-i18next"
import { NavLink } from "react-router-dom"

export function HealthSidebar() {
  const { t } = useTranslation("health")

  const SECTIONS = [
    {
      title: t("nav.section_akte"),
      items: [
        { to: "/health/uebersicht",     icon: "🗂", label: t("nav.overview") },
        { to: "/health/timeline",       icon: "📅", label: t("nav.timeline") },
        { to: "/health/conditions",     icon: "🔴", label: t("nav.conditions") },
        { to: "/health/medications",    icon: "💊", label: t("nav.medications") },
        { to: "/health/observations",   icon: "🧪", label: t("nav.observations") },
        { to: "/health/allergies",      icon: "🤧", label: t("nav.allergies") },
        { to: "/health/events",         icon: "📋", label: t("nav.events") },
        { to: "/health/imaging",        icon: "🩻", label: t("nav.imaging") },
        { to: "/health/practitioners",  icon: "👨‍⚕️", label: t("nav.practitioners") },
        { to: "/health/documents",      icon: "📄", label: t("nav.documents") },
        { to: "/health/notes",          icon: "📝", label: t("nav.notes") },
      ],
    },
    {
      title: t("nav.section_import"),
      items: [
        { to: "/health/import", icon: "📥", label: t("nav.import") },
      ],
    },
    {
      title: t("nav.section_tracking"),
      items: [
        { to: "/health/apple",  icon: "🍎", label: t("nav.apple") },
        { to: "/health/schlaf", icon: "😴", label: t("nav.sleep") },
      ],
    },
    {
      title: t("nav.section_ki"),
      items: [
        { to: "/health/ki", icon: "💬", label: t("nav.ki") },
      ],
    },
  ]

  return (
    <nav className="w-48 flex-shrink-0 flex flex-col gap-4 py-2">
      {SECTIONS.map((section) => (
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
