import { useId } from "react"
import { useDialogFokus } from "./useDialogFokus"

/**
 * Alles, was ein Overlay zum Dialog macht (docs/specs/ui-standard.md, Regel 6), in einem Aufruf:
 *
 *   const dlg = useDialog({ onEscape: onClose })
 *   <div {...dlg.props} className="fixed inset-0 …">  …  <h2 id={dlg.titelId}>Titel</h2>
 *
 * ``onEscape`` nur setzen, wenn der Dialog heute schon per Klick daneben schließt –
 * dann verliert Escape nichts, was nicht ohnehin verloren ginge.
 */
export function useDialog<T extends HTMLElement = HTMLDivElement>({ onEscape }: { onEscape?: () => void } = {}) {
  const titelId = useId()
  const ref = useDialogFokus<T>({ onEscape })
  return {
    titelId,
    ref,
    props: { ref, role: "dialog", "aria-modal": true, "aria-labelledby": titelId, tabIndex: -1 } as const,
  }
}
