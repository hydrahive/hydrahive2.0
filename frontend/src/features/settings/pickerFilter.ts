/** Ein Eintrag im Auswahlfeld (Agent, Projekt …). */
export interface PickerItem {
  id: string
  name: string
  /** Zusatzzeile, z. B. „Master · claude-sonnet-4-6“; wird mit durchsucht. */
  detail?: string
  /** Gedimmt anzeigen (deaktiviert, pausiert, archiviert). */
  dim?: boolean
}

/** Treffer in Name und Zusatz, ohne Rücksicht auf Groß/Klein; Reihenfolge bleibt. */
export function filterItems(items: PickerItem[], query: string): PickerItem[] {
  const q = query.trim().toLowerCase()
  if (!q) return items
  return items.filter((i) => i.name.toLowerCase().includes(q) || (i.detail ?? "").toLowerCase().includes(q))
}
