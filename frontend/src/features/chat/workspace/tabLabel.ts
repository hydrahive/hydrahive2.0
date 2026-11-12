import type { TFunction } from "i18next"

/** Was ein Modul für die Beschriftung seines Workspace-Reiters liefert (workspaceTabs). */
export interface TabLabelSource {
  /** Feste Beschriftung. Gilt, wenn labelKey fehlt oder sich nicht auflösen lässt. */
  label: string
  /** Schlüssel mit Namensraum, zum Beispiel "tasks:title". Dann folgt der Reiter der Sprache der Oberfläche. */
  labelKey?: string
}

/**
 * Beschriftung eines Modul-Reiters.
 *
 * Mit labelKey die Übersetzung, sonst label. Ein unbekannter Schlüssel oder eine leere Übersetzung
 * fällt auf label zurück, damit nie der rohe Schlüssel im Reiter steht. Module sind zur Laufzeit
 * eingehängt und nicht typgeprüft, deshalb wird labelKey hier geprüft.
 */
export function tabLabel(t: TFunction, tab: TabLabelSource): string {
  const key = tab.labelKey
  if (typeof key !== "string" || !key) return tab.label
  const miss = "\u0000"
  const text = t(key, { defaultValue: miss })
  return typeof text === "string" && text && text !== miss ? text : tab.label
}
