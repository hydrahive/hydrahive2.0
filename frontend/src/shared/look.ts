// Look-Presets — verändern die FORM der Oberfläche (Radius, Ränder, Glow,
// Dichte), unabhängig von der Akzentfarbe (siehe theme.ts). Zusammen ergeben
// Farbe × Look ein WordPress-artiges Theming: ein Umschalten baut die komplette
// GUI-Optik um, nicht nur die Farbe.

export type LookId = "neon" | "clean" | "compact" | "solid"

export interface LookMeta {
  id: LookId
  name: string
  description: string
}

export const LOOKS: LookMeta[] = [
  {
    id: "neon",
    name: "Neon (Standard)",
    description: "Glasige Panels, Glow-Ränder, runde Ecken — der Original-HydraHive-Look.",
  },
  {
    id: "clean",
    name: "Clean",
    description: "Flache Flächen, dünne Ränder, kaum Glow. Ruhig und sachlich.",
  },
  {
    id: "compact",
    name: "Kompakt",
    description: "Enge Abstände, kleinere Radien. Mehr Inhalt pro Bildschirm.",
  },
  {
    id: "solid",
    name: "Solid",
    description: "Kräftige Flächen, klare Kanten, hoher Kontrast. Kein Glas.",
  },
]

const STORAGE_KEY = "hh-look"

export function getStoredLook(): LookId {
  const v = (typeof localStorage !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null) as LookId | null
  if (v && LOOKS.some((l) => l.id === v)) return v
  return "neon"
}

export function applyLook(id: LookId): void {
  if (typeof document === "undefined") return
  if (id === "neon") {
    document.documentElement.removeAttribute("data-look")
  } else {
    document.documentElement.setAttribute("data-look", id)
  }
  try {
    localStorage.setItem(STORAGE_KEY, id)
  } catch {
    /* ignore */
  }
}
