// VORSCHAU Startdesktop: welcher Bereich aktiv ist, zuletzt benutzte App je Bereich,
// Vorschau an/aus. Nur im Browser (localStorage) – beim echten Einbau am Server.
import type { NavItem } from "@/shared/nav-config"
import type { FilledGroup } from "./startLogic"

const ON_KEY = "hh-startdesk-preview"
const AREA_KEY = "hh-startdesk-area"
const LAST_KEY = "hh-startdesk-last"

function read(key: string): string | null {
  try { return localStorage.getItem(key) } catch { return null }
}
function write(key: string, value: string): void {
  try { localStorage.setItem(key, value) } catch { /* privater Modus */ }
}

/** Bereichs-Leiste an? Standard: an, sobald man die Vorschau einmal geöffnet hat. */
export function previewOn(): boolean { return read(ON_KEY) === "1" }
export function setPreviewOn(on: boolean): void {
  write(ON_KEY, on ? "1" : "0")
  window.dispatchEvent(new Event("hh-startdesk-change"))
}

export function storedArea(): string | null { return read(AREA_KEY) }
export function storeArea(id: string): void { write(AREA_KEY, id) }

function lastMap(): Record<string, string> {
  try { return JSON.parse(read(LAST_KEY) ?? "{}") as Record<string, string> } catch { return {} }
}
export function rememberLast(areaId: string, path: string): void {
  write(LAST_KEY, JSON.stringify({ ...lastMap(), [areaId]: path }))
}

/** Bereich, zu dem ein Pfad gehört (längster passender App-Pfad gewinnt). */
export function areaForPath(groups: FilledGroup[], pathname: string): { area: FilledGroup; item: NavItem } | null {
  let best: { area: FilledGroup; item: NavItem } | null = null
  for (const area of groups) for (const item of area.items) {
    const hit = pathname === item.path || pathname.startsWith(`${item.path}/`)
    if (hit && (!best || item.path.length > best.item.path.length)) best = { area, item }
  }
  return best
}

/** Wohin ein Klick auf eine Bereichs-Kachel führt: zuletzt benutzte App des Bereichs, sonst die erste. */
export function entryPath(area: FilledGroup): string {
  const last = lastMap()[area.group.id]
  return area.items.some((i) => i.path === last) ? last! : area.items[0].path
}
