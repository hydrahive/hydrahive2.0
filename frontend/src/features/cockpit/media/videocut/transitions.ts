import type { CSSProperties } from "react"
import type { MediaTransitionEffect } from "../../mediaWorkspaceApi"

export interface TransitionMeta {
  id: MediaTransitionEffect
  label: string
  /** Kurz-Kürzel für den Marker. */
  short: string
}

export const TRANSITIONS: TransitionMeta[] = [
  { id: "cut", label: "Hartschnitt", short: "" },
  { id: "crossfade", label: "Überblendung", short: "X" },
  { id: "wipe", label: "Wisch", short: "W" },
  { id: "fade-black", label: "Nach Schwarz", short: "B" },
]

export function transitionLabel(effect: MediaTransitionEffect | undefined): string {
  return TRANSITIONS.find((t) => t.id === (effect ?? "cut"))?.label ?? "Hartschnitt"
}

export function transitionShort(effect: MediaTransitionEffect | undefined): string {
  return TRANSITIONS.find((t) => t.id === (effect ?? "cut"))?.short ?? ""
}

/** Style für den Overlay-Layer (Spur NACH dem Schnittpunkt) je Effekt.
 *  progress 0 → Overlay unsichtbar, 1 → Overlay voll sichtbar.
 *  Der base-Layer liegt darunter und ist immer voll sichtbar. */
export function overlayStyle(effect: MediaTransitionEffect, progress: number): CSSProperties {
  const p = Math.max(0, Math.min(1, progress))
  switch (effect) {
    case "crossfade":
      return { opacity: p }
    case "wipe":
      // Overlay wischt von links herein: rechter Teil bleibt zunächst abgeschnitten.
      return { opacity: 1, clipPath: `inset(0 ${(1 - p) * 100}% 0 0)` }
    case "fade-black":
      // Erste Hälfte: base nach Schwarz (Overlay unsichtbar). Zweite Hälfte:
      // Overlay aus Schwarz heraus. Die Schwarzblende macht OutputMonitor separat.
      return { opacity: p < 0.5 ? 0 : (p - 0.5) * 2 }
    case "cut":
    default:
      return { opacity: p >= 0.5 ? 1 : 0 }
  }
}

/** Deckkraft der Schwarzblende (nur fade-black): 1 in der Mitte, 0 an den Rändern. */
export function blackVeilOpacity(effect: MediaTransitionEffect, progress: number): number {
  if (effect !== "fade-black") return 0
  const p = Math.max(0, Math.min(1, progress))
  return 1 - Math.abs(p - 0.5) * 2
}
