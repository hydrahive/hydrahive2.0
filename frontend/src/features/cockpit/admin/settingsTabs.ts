import type { EditableSetting } from "@/features/system/settingsApi"

/**
 * Reiter der Globalen Einstellungen (Plan admin-reiter-einstellungen): ein Reiter je Gruppe, die Gruppen kommen vom
 * Server. In der Adresse steht `gruppe=<slug>` (nicht `tab=`), damit das Fenster über dem System-Fenster dessen
 * Reiter nicht verstellt.
 */

export interface SettingGroup {
  name: string
  slug: string
  settings: EditableSetting[]
}

const UMLAUTE: Record<string, string> = { ä: "ae", ö: "oe", ü: "ue", ß: "ss" }

/** Gültig als Adresswert und HTML-ID: „Home Assistant“ → `home-assistant`. */
export function groupSlug(name: string): string {
  return name.toLowerCase()
    .replace(/[äöüß]/g, (c) => UMLAUTE[c])
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
}

/** Gruppen in der Reihenfolge, in der der Server sie liefert. */
export function settingGroups(settings: EditableSetting[]): SettingGroup[] {
  const gruppen = new Map<string, SettingGroup>()
  for (const s of settings) {
    const g = gruppen.get(s.group) ?? { name: s.group, slug: groupSlug(s.group), settings: [] }
    g.settings.push(s)
    gruppen.set(s.group, g)
  }
  return [...gruppen.values()]
}

export function parseGroup(slugs: readonly string[], wert: string | null): string | null {
  return slugs.find((s) => s === wert) ?? slugs[0] ?? null
}
