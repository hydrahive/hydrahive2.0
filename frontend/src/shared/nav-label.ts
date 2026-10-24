import type { TFunction } from "i18next"
import i18n from "i18next"

type BundleOf = (ns: string) => unknown

const defaultBundle: BundleOf = (ns) => {
  try { return i18n.getResourceBundle(i18n.language || "de", ns) ?? i18n.getResourceBundle("de", ns) } catch { return undefined }
}

/**
 * Löst das Nav-Label eines Eintrags auf.
 *
 * Reihenfolge:
 *   1. nav:items.<key>          (Kern, locales/<lang>/nav.json)
 *   2. <key>:title              (Modul-Namensraum, gleicher Name wie der Schlüssel)
 *   3. <moduleId>:<key>         (Modul-Namensraum, z. B. musicplayer:musicplayer, boardgames:bg_title)
 *   4. Bündel <key> ist selbst ein Text (Modul liefert { aiSecurity: "AI-Sicherheit" } auf oberster Ebene;
 *      das kann i18next per t() nicht auflösen, geprüft 24.10.2026)
 *   5. roher Schlüssel          (Rückfall)
 * docs/specs/startdesktop.md, Punkt 6.
 */
export function navLabel(t: TFunction, labelKey: string, moduleId?: string, bundleOf: BundleOf = defaultBundle): string {
  const miss = "\u0000"
  const core = t(`items.${labelKey}`, { defaultValue: miss })
  if (core !== miss) return core
  const title = t(`${labelKey}:title`, { defaultValue: miss })
  if (title !== miss) return title
  if (moduleId) {
    const own = t(`${moduleId}:${labelKey}`, { defaultValue: miss })
    if (own !== miss) return own
  }
  const top = bundleOf(labelKey)
  if (typeof top === "string" && top) return top
  return labelKey
}
