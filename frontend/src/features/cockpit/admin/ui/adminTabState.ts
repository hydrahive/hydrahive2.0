/**
 * Reiter-Logik für Admin-Fenster (Plan admin-reiter-archiv): Der Reiter steht in der Adresse (`tab=`),
 * damit Neuladen und Lesezeichen ihn behalten. Fehlt er oder ist er unbekannt, gilt der erste Reiter.
 */

export function parseTab<T extends string>(liste: readonly T[], wert: string | null): T {
  return liste.find((id) => id === wert) ?? liste[0]
}

/** Suchteil der Adresse mit gesetztem `tab`; andere Werte bleiben in ihrer Reihenfolge. */
export function withTab(search: string, id: string): string {
  const params = new URLSearchParams(search)
  params.set("tab", id)
  return `?${params.toString()}`
}

/** Nächster (+1) bzw. voriger (−1) Reiter, am Rand geht es auf der anderen Seite weiter. */
export function nextTab<T extends string>(liste: readonly T[], aktuell: T, richtung: 1 | -1): T {
  const i = liste.indexOf(aktuell)
  return liste[(i + richtung + liste.length) % liste.length]
}
