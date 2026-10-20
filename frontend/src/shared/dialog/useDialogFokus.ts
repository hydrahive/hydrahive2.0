import { useCallback, useEffect, useRef } from "react"
import { fokussierbare, oberster, tabZiel } from "./focusTrap"

interface Optionen {
  /** Escape schließt den Dialog. Weglassen, wenn Escape nichts tun soll (z. B. ungesicherte Eingaben). */
  onEscape?: () => void
}

/**
 * Macht ein Overlay zum echten Dialog für die Tastatur (docs/specs/ui-standard.md, Regel 6):
 * Fokus beim Öffnen hinein, Tab bleibt drin, Escape optional, beim Schließen
 * Fokus zurück zum Auslöser.
 *
 * Liefert eine Callback-Ref fürs Dialog-Element (tabIndex={-1}). Sie greift, sobald das
 * Element erscheint, und räumt auf, sobald es verschwindet – auch wenn die Komponente
 * selbst gemountet bleibt und nur bedingt rendert (z. B. ``if (!offen) return null``).
 */
export function useDialogFokus<T extends HTMLElement>({ onEscape }: Optionen = {}) {
  const escRef = useRef(onEscape)
  useEffect(() => { escRef.current = onEscape }, [onEscape])
  const aufraeumen = useRef<(() => void) | null>(null)

  const ref = useCallback((dialog: T | null) => {
    aufraeumen.current?.()
    aufraeumen.current = dialog ? einhaengen(dialog, () => escRef.current) : null
  }, [])

  // Unmount der Komponente bei offenem Dialog
  useEffect(() => () => { aufraeumen.current?.() }, [])
  return ref
}

function einhaengen(dialog: HTMLElement, escape: () => (() => void) | undefined): () => void {
  const ausloeser = document.activeElement instanceof HTMLElement ? document.activeElement : null

  // Fokus hinein – aber nicht stehlen, wenn ein Kind (autoFocus) ihn schon hat.
  if (!dialog.contains(document.activeElement)) {
    const [erstes] = fokussierbare(dialog)
    ;(erstes ?? dialog).focus({ preventScroll: true })
  }

  const onKeyDown = (e: KeyboardEvent) => {
    // Nur der oberste offene Dialog reagiert (verschachtelte Dialoge).
    const alle = Array.from(document.querySelectorAll<HTMLElement>("[aria-modal='true']"))
    if (oberster(alle) !== dialog) return
    const esc = escape()
    if (e.key === "Escape" && esc) {
      e.stopPropagation()
      esc()
      return
    }
    if (e.key !== "Tab") return
    const ziel = tabZiel(fokussierbare(dialog), document.activeElement, e.shiftKey, dialog)
    if (ziel) {
      e.preventDefault()
      ziel.focus()
    }
  }
  document.addEventListener("keydown", onKeyDown, true)
  return () => {
    document.removeEventListener("keydown", onKeyDown, true)
    // Fokus zurück, wenn der Auslöser noch da ist und der Fokus nicht schon woanders sinnvoll steht.
    if (ausloeser && ausloeser.isConnected && (!document.activeElement || document.activeElement === document.body || dialog.contains(document.activeElement))) {
      ausloeser.focus({ preventScroll: true })
    }
  }
}
