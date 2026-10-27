// Bereiche der Startseite und der Bereichs-Leiste (docs/specs/startdesktop.md).
// Module können ihren Bereich selbst über nav.area angeben – das hat Vorrang vor `paths` hier.
import type { LucideIcon } from "lucide-react"
import { Bot, Boxes, Clapperboard, Feather, Gamepad2, House, MessagesSquare, Settings2, Telescope } from "lucide-react"

export interface Area {
  id: string
  title: string
  /** Ein Satz, was man hier macht – einfache Sprache. */
  blurb: string
  icon: LucideIcon
  /** Tailwind-Klassen: Verlauf, Rand, Textfarbe. */
  tone: string
  /** Nur die Textfarbe aus `tone` (für Symbole, aktive Reiter). */
  text: string
  /** Pfade der Apps, in Anzeige-Reihenfolge. */
  paths: string[]
  adminOnly?: boolean
  /** Hydra-Kopf als Deko der Kachel (public/startdesk/koepfe/, Task 0dda5420). */
  head: string
}

export const AREAS: Area[] = [
  { id: "medien", title: "Medienstudio", blurb: "Filme, Bilder, Musik und Ton machen", icon: Clapperboard,
    tone: "from-[#ff6fae]/20 border-[#ff6fae]/40", text: "text-[#ff9cc8]", head: "/startdesk/koepfe/kopf-3-orange.webp",
    paths: ["/studio", "/atelier", "/videoeditor", "/tonstudio", "/musicplayer", "/media"] },
  { id: "schreiben", title: "Schreibbüro", blurb: "Bücher, Notizen und Pläne schreiben", icon: Feather,
    tone: "from-[#fbbf24]/20 border-[#fbbf24]/40", text: "text-[#fcd34d]", head: "/startdesk/koepfe/kopf-5-brille.webp",
    paths: ["/storyteller", "/notizbuch", "/scratchpad", "/diagramme", "/blueprint"] },
  { id: "wissen", title: "Wissen & Recherche", blurb: "Suchen, nachlesen, Quellen sammeln", icon: Telescope,
    tone: "from-[#69d7ff]/20 border-[#69d7ff]/40", text: "text-[#9be6ff]", head: "/startdesk/koepfe/kopf-4-tuerkis.webp",
    paths: ["/deepresearch", "/archiver", "/recht", "/datamining", "/memory", "/opentor"] },
  { id: "agenten", title: "Arbeiten mit Agenten", blurb: "Projekte, Chats und Aufgaben", icon: Bot,
    tone: "from-[#8b5cf6]/25 border-[#8b5cf6]/45", text: "text-[#c4b5fd]", head: "/startdesk/koepfe/kopf-2-lila.webp",
    paths: ["/projects", "/werkstatt", "/buddy", "/tickets", "/settings/agents", "/skills", "/butler", "/zahnfee"] },
  { id: "kommunikation", title: "Kommunikation", blurb: "Mails, Nachrichten und Telefon", icon: MessagesSquare,
    tone: "from-[#34d399]/20 border-[#34d399]/40", text: "text-[#6ee7b7]", head: "/startdesk/koepfe/kopf-1-mint.webp",
    paths: ["/mailbox", "/communication", "/teamchat", "/voip", "/voice"] },
  { id: "zuhause", title: "Zuhause & Privat", blurb: "Geld, Gesundheit und Haus", icon: House,
    tone: "from-[#f97316]/20 border-[#f97316]/40", text: "text-[#fdba74]", head: "/startdesk/koepfe/kopf-1-mint.webp",
    paths: ["/haushaltsbuch", "/akte", "/homeassistant", "/vault", "/cryptoboard", "/mining", "/vitrine"] },
  { id: "freizeit", title: "Freizeit", blurb: "Filme finden, spielen, abschalten", icon: Gamepad2,
    tone: "from-[#22d3ee]/20 border-[#22d3ee]/40", text: "text-[#67e8f9]", head: "/startdesk/koepfe/kopf-2-lila.webp",
    paths: ["/mediacenter", "/boardgames", "/minigames", "/vr", "/streaming"] },
  { id: "verwaltung", title: "Verwaltung", blurb: "System, Benutzer und Server", icon: Settings2,
    tone: "from-[#94a3b8]/20 border-[#94a3b8]/40", text: "text-[#cbd5e1]", head: "/startdesk/koepfe/kopf-5-brille.webp", adminOnly: true,
    paths: ["/admin", "/dashboard", "/vms", "/containers", "/federation", "/mcp", "/plugins", "/ai-security"] },
]

/** Nirgends zeigen. */
export const HIDDEN_PATHS = ["/example", "/help", "/settings/projects"]

/** Sammel-Bereich für alles ohne Zuordnung (z. B. neue Module ohne nav.area). */
export const OTHER_AREA: Area = {
  id: "weitere", title: "Weitere", blurb: "Noch nicht einsortiert", icon: Boxes,
  tone: "from-white/10 border-white/20", text: "text-zinc-300", head: "/startdesk/koepfe/kopf-4-tuerkis.webp", paths: [],
}
