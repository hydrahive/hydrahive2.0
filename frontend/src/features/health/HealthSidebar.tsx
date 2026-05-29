import { NavLink } from "react-router-dom"

interface SectionItem {
  to: string
  icon: string
  label: string
}

interface Section {
  title: string
  items: SectionItem[]
}

const SECTIONS: Section[] = [
  {
    title: "Patientenakte",
    items: [
      { to: "/health/uebersicht", icon: "🗂", label: "Übersicht" },
      { to: "/health/zeitstrahl", icon: "📅", label: "Zeitstrahl" },
    ],
  },
  {
    title: "Medizinisch",
    items: [
      { to: "/health/diagnosen",   icon: "🔴", label: "Diagnosen" },
      { to: "/health/medikamente", icon: "💊", label: "Medikamente" },
      { to: "/health/laborwerte",  icon: "🧪", label: "Laborwerte" },
      { to: "/health/allergien",   icon: "🤧", label: "Allergien" },
      { to: "/health/impfungen",   icon: "💉", label: "Impfungen" },
      { to: "/health/eingriffe",   icon: "🔪", label: "Eingriffe" },
    ],
  },
  {
    title: "Kontakte",
    items: [
      { to: "/health/arztbesuche",  icon: "🏥", label: "Arztbesuche" },
      { to: "/health/abrechnung",   icon: "🧾", label: "Abrechnung" },
      { to: "/health/krankenhaus",  icon: "🛏", label: "Krankenhaus" },
      { to: "/health/befunde",      icon: "📋", label: "Befunde" },
      { to: "/health/dokumente",    icon: "📄", label: "Dokumente" },
    ],
  },
  {
    title: "Tracking",
    items: [
      { to: "/health/apple",  icon: "🍎", label: "Apple Health" },
      { to: "/health/schlaf", icon: "😴", label: "Schlaf" },
    ],
  },
  {
    title: "Forschung",
    items: [
      { to: "/health/forschungs-apis", icon: "🔬", label: "Forschungs-APIs" },
    ],
  },
  {
    title: "KI",
    items: [
      { to: "/health/ki", icon: "💬", label: "KI-Assistent" },
    ],
  },
]

export function HealthSidebar() {
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
