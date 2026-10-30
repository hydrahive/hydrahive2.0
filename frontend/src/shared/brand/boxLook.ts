import type { CSSProperties } from "react"
import { BOX_THEMES, type BoxTheme } from "./boxThemes"

/**
 * Kopffarbe + Zustand einer Box (Plan docs/plans/farbstufen-kopffarben.md, Till: „Variante Kopffarben“).
 * Regel: Jede Box mit Thema trägt die Farbe ihres Hydra-Kopfs. Warnung (gelb) und Fehler (rot) übermalen sie,
 * damit sie immer auffallen – auch beim Professor, dessen Kopf selbst amber ist. Farbe nie allein: das Schild
 * (BoxStatus) trägt Symbol + Wort.
 */
export type BoxStatus = "warnung" | "fehler" | "ok"

export const STATUS_FARBE: Record<BoxStatus, string> = {
  warnung: "#fbbf24",
  fehler: "#fb7185",
  ok: "#34d399",
}

export interface BoxLook {
  /** Farbe des 4-px-Streifens links; null = kein Streifen. */
  streifen: string | null
  /** Tönung, die von links in die Kopfzeile läuft; null = keine. */
  kopfTon: string | null
  /** Farbiger Rand (nur Warnung/Fehler); null = Standardrand. */
  rand: string | null
  /** Schild oben rechts; null = keins. */
  schild: BoxStatus | null
}

function rgb(hex: string, alpha: number): string {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
  return `rgb(${r} ${g} ${b} / ${alpha})`
}

export function boxLook(theme?: BoxTheme, status?: BoxStatus): BoxLook {
  if (status === "warnung" || status === "fehler") {
    const f = STATUS_FARBE[status]
    return { streifen: f, kopfTon: rgb(f, 0.16), rand: rgb(f, 0.45), schild: status }
  }
  const schild = status ?? null
  if (!theme) return { streifen: null, kopfTon: null, rand: null, schild }
  const f = BOX_THEMES[theme].farbe
  return { streifen: f, kopfTon: rgb(f, 0.09), rand: null, schild }
}

/** Inline-Stil für die Box-Fläche: Streifen links + ggf. farbiger Rand. Kanten einzeln (React mischt Kurzformen falsch). */
export function boxRahmenStil(l: BoxLook): CSSProperties {
  const stil: CSSProperties = {}
  if (l.rand) Object.assign(stil, { borderTopColor: l.rand, borderRightColor: l.rand, borderBottomColor: l.rand })
  if (l.streifen) Object.assign(stil, { borderLeftColor: l.streifen, borderLeftWidth: 4 })
  return stil
}

/** Inline-Stil für die Kopfzeile: Tönung läuft von links in die Kopf-Stufe aus. */
export function kopfTonStil(l: BoxLook): CSSProperties | undefined {
  return l.kopfTon ? { backgroundImage: `linear-gradient(90deg, ${l.kopfTon}, transparent 70%)` } : undefined
}
