import type { AdminOverlayId } from "./adminOverlayRegistry"

/** URL-Teile, die zu genau einem Fenster gehören und beim Wechsel/Schließen wegmüssen. */
const OVERLAY_SCOPED = ["container", "tab"]

/** Neue Such-Parameter für einen Fensterwechsel; fremde Parameter bleiben, die Eingabe bleibt unverändert. */
export function nextOverlayParams(current: URLSearchParams, overlay: AdminOverlayId | null): URLSearchParams {
  const next = new URLSearchParams(current)
  OVERLAY_SCOPED.forEach((key) => next.delete(key))
  if (overlay) next.set("section", overlay)
  else next.delete("section")
  return next
}
