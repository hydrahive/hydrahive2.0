import type { TFunction } from "i18next"

/**
 * Löst das Nav-Label eines Eintrags auf.
 *
 * Core-Items leben unter `nav:items.<key>` (siehe locales/<lang>/nav.json).
 * Installierte Module bringen keinen Eintrag im nav-Namespace mit — sie liefern
 * ihren Titel im EIGENEN Namespace unter `<key>:title`. Reihenfolge daher:
 *   1. nav:items.<key>   (Core)
 *   2. <key>:title       (Modul-Namespace)
 *   3. roher Key         (Fallback, falls beides fehlt)
 *
 * `t` ist an den nav-Namespace gebunden; `<key>:title` nutzt den expliziten
 * i18next-Namespace-Präfix und greift damit über nav hinaus.
 */
export function navLabel(t: TFunction, labelKey: string): string {
  return t(`items.${labelKey}`, {
    defaultValue: t(`${labelKey}:title`, { defaultValue: labelKey }),
  })
}
