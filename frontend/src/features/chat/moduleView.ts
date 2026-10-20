/** Modul-Ansicht im Chat (docs/specs/module-view-sandbox.md §2.3): reine Prüf-Helfer, ohne React. */

const MODULE_RE = /^[a-z0-9][a-z0-9-]*$/
const VIEW_RE = /^[A-Za-z0-9_-]{1,64}$/

/** Rechte des Rahmens – bewusst OHNE allow-same-origin, allow-top-navigation und allow-forms. */
export const FRAME_SANDBOX = "allow-scripts allow-popups allow-popups-to-escape-sandbox"

export interface ModuleView {
  module: string
  view_id: string
  title: string
}

/** API-Pfad (ohne /api) für die signierte Ansichts-Adresse – null bei ungültigen IDs. */
export function viewLinkPath(module: string, viewId: string): string | null {
  if (!MODULE_RE.test(module) || !VIEW_RE.test(viewId)) return null
  return `/modules/${module}/view-link/${viewId}`
}

/** Nur relative Adressen unter /api/module-device/<module>/sandbox/ ohne Pfad-Tricks werden geladen. */
export function isSandboxUrl(module: string, url: unknown): url is string {
  if (typeof url !== "string" || !MODULE_RE.test(module)) return false
  const prefix = `/api/module-device/${module}/sandbox/`
  if (!url.startsWith(prefix) || url.startsWith("//")) return false
  const path = url.split(/[?#]/, 1)[0]
  return !path.split("/").some((part) => part === ".." || part === ".")
}
