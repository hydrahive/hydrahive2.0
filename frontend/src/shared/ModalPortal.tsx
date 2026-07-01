import type { ReactNode } from "react"
import { createPortal } from "react-dom"

/** Rendert Kinder via Portal an ``document.body``.
 *
 * Nötig für Overlays mit ``position: fixed``, die INNERHALB einer ``.box``
 * (oder eines anderen Elements mit ``transform``/``filter``/``perspective``)
 * gerendert werden: ein transformierter Vorfahr wird zum Containing-Block für
 * ``fixed`` → das Overlay positioniert sich dann relativ zu diesem Element statt
 * zum Viewport. Da ``.box:hover`` ein ``transform: translateY(-2px)`` setzt,
 * „springt“ so ein Modal beim Mausbewegen zwischen Box- und Viewport-Bezug.
 * Das Portal hängt das Overlay ans ``body`` — außerhalb jeder Box → stabil.
 */
export function ModalPortal({ children }: { children: ReactNode }) {
  if (typeof document === "undefined") return null
  return createPortal(children, document.body)
}
