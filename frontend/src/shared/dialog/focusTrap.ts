/**
 * Fokusführung für Dialoge (docs/specs/ui-standard.md, Regel 6).
 *
 * Reine Logik ohne React: welches Element bekommt bei Tab / Shift+Tab den Fokus,
 * damit die Tastatur den offenen Dialog nicht verlässt.
 */

export const FOKUSSIERBAR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled]):not([type=hidden])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
  "[contenteditable='true']",
].join(",")

/** Alle per Tab erreichbaren, sichtbaren Elemente im Container, in DOM-Reihenfolge. */
export function fokussierbare(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOKUSSIERBAR)).filter(
    (el) => !el.hasAttribute("inert") && !el.closest("[inert],[hidden],[aria-hidden='true']") && sichtbar(el),
  )
}

function sichtbar(el: HTMLElement): boolean {
  // jsdom/SSR kennen kein Layout: dort zählt jedes Element als sichtbar.
  if (typeof el.getClientRects !== "function" || el.getClientRects().length > 0) return true
  return el.offsetParent !== null || getComputedStyle(el).position === "fixed"
}

/**
 * Ziel für Tab im Dialog. ``null`` = Browser darf normal weiter (Fokus bleibt sowieso drin).
 *
 * @param liste   fokussierbare Elemente des Dialogs (DOM-Reihenfolge)
 * @param aktiv   aktuell fokussiertes Element (kann außerhalb liegen)
 * @param zurueck Shift+Tab
 */
export function tabZiel(
  liste: readonly HTMLElement[],
  aktiv: Element | null,
  zurueck: boolean,
  container: HTMLElement,
): HTMLElement | null {
  if (liste.length === 0) return container          // nichts Bedienbares: Fokus auf den Dialog selbst
  const erstes = liste[0]
  const letztes = liste[liste.length - 1]
  const drin = !!aktiv && container.contains(aktiv)
  if (!drin) return zurueck ? letztes : erstes      // Fokus war draußen: zurück hinein
  if (zurueck && (aktiv === erstes || aktiv === container)) return letztes
  if (!zurueck && aktiv === letztes) return erstes
  return null
}
