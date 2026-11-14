/** Büro-Grafiken: ein Hintergrund + ein Charakter-Bild pro Template-Gruppe (Spec agent-office.md
 *  §4.1, Etappe 3). Generiert mit generate_image, einmalig, lokal unter public/office/ abgelegt. */
export const OFFICE_BACKGROUND = "/office/office-bg.webp"

const CHAR_IMAGES: Record<string, string> = {
  personal: "/office/char-personal.webp",
  projects: "/office/char-projects.webp",
  specialists: "/office/char-specialists.webp",
  modules: "/office/char-modules.webp",
  system: "/office/char-system.webp",
}

const FALLBACK_GROUP = "specialists"

/** Bildpfad für eine Template-Gruppe; unbekannt/fehlend fällt auf `specialists` zurück. */
export function charImageForGroup(group: string | undefined): string {
  return CHAR_IMAGES[group ?? FALLBACK_GROUP] ?? CHAR_IMAGES[FALLBACK_GROUP]
}
