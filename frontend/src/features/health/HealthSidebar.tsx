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
    title: "Meine Akte",
    items: [
      { to: "/health/uebersicht",     icon: "🗂", label: "Übersicht" },
      { to: "/health/timeline",       icon: "📅", label: "Zeitstrahl" },
      { to: "/health/conditions",    icon: "🔴", label: "Diagnosen" },
      { to: "/health/medications",   icon: "💊", label: "Medikamente" },
      { to: "/health/observations",   icon: "🧪", label: "Laborwerte" },
      { to: "/health/allergies",     icon: "🤧", label: "Allergien" },
      { to: "/health/events",        icon: "📋", label: "Ereignisse" },
      { to: "/health/imaging",       icon: "🩻", label: "Bildgebung" },
      { to: "/health/practitioners", icon: "👨‍⚕️", label: "Ärzte" },
      { to: "/health/documents",     icon: "📄", label: "Dokumente" },
      { to: "/health/notes",         icon: "📝", label: "Notizen" },
    ],
  },
  {
    title: "Import",
    items: [
      { to: "/health/import", icon: "📥", label: "eGA / FHIR" },
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