import type { AdminOverlayId } from "@/features/cockpit/admin/adminOverlayRegistry"

/** Themen der Boxen: jedes Thema hat einen festen Kopf von Tills Hydra (Task 0dda5420, Till: „fester Kopf nach Thema“). */
export type BoxTheme = "wissen" | "werkzeug" | "status" | "ideen" | "kontakt"

interface ThemeLook {
  name: string
  head: string
  /** Kopffarbe (Streifen links + Tönung der Kopfzeile, siehe boxLook). */
  farbe: string
  /** Rand + Hintergrund des Kopf-Kreises. */
  ring: string
  /** Feiner Verlauf oben in der Box. */
  wash: string
}

const K = "/startdesk/koepfe"

export const BOX_THEMES: Record<BoxTheme, ThemeLook> = {
  wissen: { farbe: "#fbbf24", name: "Professor", head: `${K}/kopf-5-brille.webp`, ring: "border-[#fbbf24]/40 bg-[#fbbf24]/10", wash: "from-[#fbbf24]/[7%]" },
  werkzeug: { farbe: "#f97316", name: "Macher", head: `${K}/kopf-3-orange.webp`, ring: "border-[#f97316]/40 bg-[#f97316]/10", wash: "from-[#f97316]/[7%]" },
  status: { farbe: "#22d3ee", name: "Denker", head: `${K}/kopf-4-tuerkis.webp`, ring: "border-[#22d3ee]/40 bg-[#22d3ee]/10", wash: "from-[#22d3ee]/[7%]" },
  ideen: { farbe: "#a78bfa", name: "Träumer", head: `${K}/kopf-2-lila.webp`, ring: "border-[#a78bfa]/40 bg-[#a78bfa]/10", wash: "from-[#a78bfa]/[8%]" },
  kontakt: { farbe: "#34d399", name: "Buddy", head: `${K}/kopf-1-mint.webp`, ring: "border-[#34d399]/40 bg-[#34d399]/10", wash: "from-[#34d399]/[7%]" },
}

/** Fester Kopf je Admin-Fenster (eine Stelle statt in 20 Dateien). */
export const ADMIN_OVERLAY_THEME: Record<AdminOverlayId, BoxTheme> = {
  users: "kontakt", credentials: "kontakt", access: "kontakt",
  modules: "werkzeug", plugins: "werkzeug", extensions: "werkzeug", containers: "werkzeug",
  vms: "werkzeug", nodes: "werkzeug", jobs: "werkzeug", "scheduled-tasks": "werkzeug", archive: "werkzeug",
  system: "status", "system-settings": "status",
  llm: "ideen", mcp: "ideen", federation: "ideen",
  zahnfee: "wissen",
}
