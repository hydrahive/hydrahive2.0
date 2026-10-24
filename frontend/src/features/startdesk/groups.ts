// VORSCHAU Startdesktop (Task 7876c5df) – Gruppen-Zuordnung zum Umsortieren mit Till.
// Diese Datei ist die einzige Stelle, an der festgelegt wird, welche App in welcher Kachel steht.
import type { LucideIcon } from "lucide-react"
import { Clapperboard, Feather, Telescope, Bot, MessagesSquare, House, Gamepad2, Settings2, Boxes } from "lucide-react"

export interface StartGroup {
  id: string
  title: string
  /** Ein Satz, was man hier macht – in einfacher Sprache. */
  blurb: string
  icon: LucideIcon
  /** Farbton der Kachel (Tailwind-Klassen für Rand/Text/Hintergrund). */
  tone: string
  /** Pfade der Apps in dieser Gruppe, in Anzeige-Reihenfolge. */
  paths: string[]
  adminOnly?: boolean
}

export const START_GROUPS: StartGroup[] = [
  { id: "medien", title: "Medienstudio", blurb: "Filme, Bilder, Musik und Ton machen", icon: Clapperboard,
    tone: "from-[#ff6fae]/20 border-[#ff6fae]/40 text-[#ff9cc8]",
    paths: ["/studio", "/atelier", "/videoeditor", "/tonstudio", "/musicplayer", "/media"] },
  { id: "schreiben", title: "Schreibbüro", blurb: "Bücher, Notizen und Pläne schreiben", icon: Feather,
    tone: "from-[#fbbf24]/20 border-[#fbbf24]/40 text-[#fcd34d]",
    paths: ["/storyteller", "/notizbuch", "/scratchpad", "/diagramme", "/blueprint"] },
  { id: "wissen", title: "Wissen & Recherche", blurb: "Suchen, nachlesen, Quellen sammeln", icon: Telescope,
    tone: "from-[#69d7ff]/20 border-[#69d7ff]/40 text-[#9be6ff]",
    paths: ["/deepresearch", "/archiver", "/recht", "/datamining", "/memory", "/opentor"] },
  { id: "agenten", title: "Arbeiten mit Agenten", blurb: "Projekte, Chats und Aufgaben", icon: Bot,
    tone: "from-[#8b5cf6]/25 border-[#8b5cf6]/45 text-[#c4b5fd]",
    paths: ["/projects", "/werkstatt", "/buddy", "/tickets", "/settings/agents", "/skills", "/butler", "/zahnfee"] },
  { id: "kommunikation", title: "Kommunikation", blurb: "Mails, Nachrichten und Telefon", icon: MessagesSquare,
    tone: "from-[#34d399]/20 border-[#34d399]/40 text-[#6ee7b7]",
    paths: ["/mailbox", "/communication", "/teamchat", "/voip", "/voice"] },
  { id: "zuhause", title: "Zuhause & Privat", blurb: "Geld, Gesundheit und Haus", icon: House,
    tone: "from-[#f97316]/20 border-[#f97316]/40 text-[#fdba74]",
    paths: ["/haushaltsbuch", "/akte", "/homeassistant", "/vault", "/cryptoboard", "/mining", "/vitrine"] },
  { id: "freizeit", title: "Freizeit", blurb: "Filme finden, spielen, abschalten", icon: Gamepad2,
    tone: "from-[#22d3ee]/20 border-[#22d3ee]/40 text-[#67e8f9]",
    paths: ["/mediacenter", "/boardgames", "/minigames", "/vr", "/streaming"] },
  { id: "verwaltung", title: "Verwaltung", blurb: "System, Benutzer und Einstellungen", icon: Settings2,
    tone: "from-[#94a3b8]/20 border-[#94a3b8]/40 text-[#cbd5e1]", adminOnly: true,
    paths: ["/admin", "/settings", "/dashboard", "/vms", "/containers", "/federation", "/mcp", "/plugins", "/ai-security"] },
]

/** Apps, die nirgends stehen sollen. */
export const HIDDEN_PATHS = ["/example", "/help", "/settings/projects"]

/** Sammelkachel für alles, was keiner Gruppe zugeordnet ist (z. B. neue Module). */
export const OTHER_GROUP: StartGroup = {
  id: "weitere", title: "Weitere", blurb: "Noch nicht einsortiert", icon: Boxes,
  tone: "from-white/10 border-white/20 text-zinc-300", paths: [],
}

/** VORSCHAU: feste Anzeigenamen. Einige Module liefern heute nur ihren internen Schlüssel
 *  („aiSecurity“, „musicplayer“, „bg_title“) – das betrifft auch die obere Leiste und wird beim
 *  echten Einbau an der Wurzel behoben. */
export const LABELS: Record<string, string> = {
  "/studio": "Studio (Film)", "/atelier": "Atelier", "/videoeditor": "Video-Editor", "/tonstudio": "Tonstudio",
  "/musicplayer": "Mediaplayer", "/media": "Media-Projekte",
  "/storyteller": "Storyteller", "/notizbuch": "Notizbuch", "/scratchpad": "Scratchpad", "/diagramme": "Diagramme", "/blueprint": "Blueprint",
  "/deepresearch": "Deep Research", "/archiver": "Archiv", "/recht": "Recht", "/datamining": "Datamining", "/memory": "Gedächtnis", "/opentor": "OpenTor OSINT",
  "/projects": "Projekte", "/werkstatt": "Werkstatt (Chat)", "/buddy": "Buddy", "/tickets": "Tickets", "/settings/agents": "Agenten",
  "/skills": "Skills", "/butler": "Butler (Abläufe)", "/zahnfee": "Zahnfee",
  "/mailbox": "Mailbox", "/communication": "Messenger", "/teamchat": "Team-Chat", "/voip": "Telefon (VoIP)", "/voice": "Sprachassistent",
  "/haushaltsbuch": "Haushaltsbuch", "/akte": "Meine Akte", "/homeassistant": "Home Assistant", "/vault": "Tresor (Vault)",
  "/cryptoboard": "Krypto-Kurse", "/mining": "Mining", "/vitrine": "Vitrine",
  "/mediacenter": "Mediacenter", "/boardgames": "Brettspiele", "/minigames": "Minispiele", "/vr": "VR-Brille", "/streaming": "Streaming",
  "/admin": "Admin", "/settings": "Einstellungen", "/dashboard": "Systemstatus", "/vms": "VMs", "/containers": "Container",
  "/federation": "Föderation", "/mcp": "MCP-Server", "/plugins": "Plugins", "/ai-security": "AI-Sicherheit",
}
