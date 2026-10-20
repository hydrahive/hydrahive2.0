import { useEffect, useRef } from "react"
import { fokussierbare, tabZiel } from "./focusTrap"

interface Optionen {
  /** Escape schließt den Dialog. Weglassen, wenn Escape nichts tun soll (z. B. ungesicherte Eingaben). */
  onEscape?: () => void
}

/**
 * Macht ein Overlay zum echten Dialog für die Tastatur (docs/specs/ui-standard.md, Regel 6):
 * Fokus beim Öffnen hinein, Tab bleibt drin, Escape optional, beim Schließen
 * Fokus zurück zum Auslöser. Ref an das Dialog-Element hängen (tabIndex={-1}).
 */
export function useDialogFokus<T extends HTMLElement>({ onEscape }: Optionen = {}) {
  const ref = useRef<T>(null)
  const escRef = useRef(onEscape)
  useEffect(() => { escRef.current = onEscape }, [onEscape])

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    const ausloeser = document.activeElement instanceof HTMLElement ? document.activeElement : null

    // Fokus hinein – aber nicht stehlen, wenn ein Kind (autoFocus) ihn schon hat.
    if (!dialog.contains(document.activeElement)) {
      const [erstes] = fokussierbare(dialog)
      ;(erstes ?? dialog).focus({ preventScroll: true })
    }

    const onKeyDown = (e: KeyboardEvent) => {
      // Nur der oberste Dialog reagiert (verschachtelte Dialoge).
      if (!istOberster(dialog)) return
      if (e.key === "Escape" && escRef.current) {
        e.stopPropagation()
        escRef.current()
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
      // Fokus zurück, wenn der Auslöser noch da ist.
      if (ausloeser && ausloeser.isConnected) ausloeser.focus({ preventScroll: true })
    }
  }, [])

  return ref
}

function istOberster(dialog: HTMLElement): boolean {
  const alle = document.querySelectorAll("[aria-modal='true']")
  return alle.length === 0 || alle[alle.length - 1] === dialog
}
