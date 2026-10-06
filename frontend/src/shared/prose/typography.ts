/** Typografie je Sprache für TipTaps Typography-Erweiterung: Anführungszeichen und Strich. */
export interface TypographySet {
  openDoubleQuote: string
  closeDoubleQuote: string
  openSingleQuote: string
  closeSingleQuote: string
  /** Ersetzt „--“ beim Tippen. Deutsch: Halbgeviertstrich (–), Englisch: Geviertstrich (—). */
  emDash: string
}

const SETS: Record<string, TypographySet> = {
  de: { openDoubleQuote: "„", closeDoubleQuote: "“", openSingleQuote: "‚", closeSingleQuote: "‘", emDash: "–" },
  en: { openDoubleQuote: "“", closeDoubleQuote: "”", openSingleQuote: "‘", closeSingleQuote: "’", emDash: "—" },
  fr: { openDoubleQuote: "« ", closeDoubleQuote: " »", openSingleQuote: "‹ ", closeSingleQuote: " ›", emDash: "–" },
}

/** Sprachcode wie „de“, „de-AT“, „en-GB“ → passende Zeichen; unbekannt → Englisch. */
export function typographyFor(language: string | undefined): TypographySet {
  const base = (language ?? "").toLowerCase().split(/[-_]/)[0]
  return SETS[base] ?? SETS.en
}
