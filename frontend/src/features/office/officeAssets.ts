/** Büro-Grafiken: ein Hintergrund + ein Charakter-Bild pro Template-Gruppe (Spec agent-office.md
 *  §4.1, Etappe 3). Generiert mit generate_image, einmalig, lokal unter public/office-media/ abgelegt.
 *
 *  Bewusst NICHT public/office/ (Bug #714→Fix, 14.11.2026): die Route heißt /office — ein gleich-
 *  benannter Asset-Ordner landet nach dem Build 1:1 als physisches Verzeichnis dist/office/, das
 *  nginx vor der SPA-Fallback-Route matcht und ohne autoindex mit 403 statt der React-Seite antwortet. */
export const OFFICE_BACKGROUND = "/office-media/office-bg.webp"

const CHAR_IMAGES: Record<string, string> = {
  personal: "/office-media/char-personal.webp",
  projects: "/office-media/char-projects.webp",
  specialists: "/office-media/char-specialists.webp",
  modules: "/office-media/char-modules.webp",
  system: "/office-media/char-system.webp",
}

const FALLBACK_GROUP = "specialists"

/** Bildpfad für eine Template-Gruppe; unbekannt/fehlend fällt auf `specialists` zurück. */
export function charImageForGroup(group: string | undefined): string {
  return CHAR_IMAGES[group ?? FALLBACK_GROUP] ?? CHAR_IMAGES[FALLBACK_GROUP]
}
