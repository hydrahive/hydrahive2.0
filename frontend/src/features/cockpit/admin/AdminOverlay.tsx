import { useId, type ReactNode } from "react"
import { X } from "lucide-react"
import { useDialogFokus } from "@/shared/dialog/useDialogFokus"
import { BoxHead } from "@/shared/brand/BoxHead"
import { BOX_THEMES, type BoxTheme } from "@/shared/brand/boxThemes"

interface Props {
  eyebrow?: string
  title: string
  /** Optionale Aktionen rechts im Header (z. B. "+ Neu"). */
  headerActions?: ReactNode
  /** Optionale Leiste unten (z. B. Speichern/Abbrechen). Ohne footer nur "Schließen". */
  footer?: ReactNode
  onClose: () => void
  children: ReactNode
  /** Maximale Breite; Default max-w-4xl. */
  maxWidthClass?: string
  /** Thema des Fensters: fester Hydra-Kopf links im Kopf + Verlauf in dessen Farbe. */
  theme?: BoxTheme
}

/**
 * Einheitlicher Cockpit-Overlay-Rahmen für Admin-Unterbereiche.
 *
 * Verhalten wie bei den Projekt-Overlays: bewusst KEIN Schließen bei Klick auf
 * den Backdrop — der Overlay schließt nur über den X-/Schließen-Button oder
 * Abbrechen/Speichern des jeweiligen Inhalts. So gehen keine Eingaben durch
 * einen versehentlichen Außenklick verloren. Aus demselben Grund schließt auch
 * Escape nicht. Tastatur: Fokus beim Öffnen hinein, Tab bleibt im Overlay,
 * danach zurück zum Auslöser (docs/specs/ui-standard.md, Regel 6).
 */
export function AdminOverlay({ eyebrow, title, headerActions, footer, onClose, children, maxWidthClass = "max-w-4xl", theme }: Props) {
  const titelId = useId()
  const dialogRef = useDialogFokus<HTMLDivElement>()
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby={titelId} tabIndex={-1}
        className={`flex h-[90dvh] w-full ${maxWidthClass} flex-col overflow-hidden rounded-[6px] border border-[#2a364b] bg-[#0e1420] shadow-2xl outline-none`}>
        <header data-box-theme={theme}
          className={`flex shrink-0 items-center gap-3 border-b border-[#2a364b] px-4 py-3 ${theme ? `bg-gradient-to-r ${BOX_THEMES[theme].wash} to-[#131b2a] to-60%` : "bg-[#131b2a]"}`}>
          {theme && <BoxHead theme={theme} />}
          <div className="min-w-0">
            {eyebrow && <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#69d7ff]">{eyebrow}</p>}
            <h2 id={titelId} className="truncate text-lg font-black text-[#e8eef8]">{title}</h2>
          </div>
          <div className="flex-1" />
          {headerActions}
          <button onClick={onClose} className="rounded-[4px] p-2 text-[#8d9ab0] hover:bg-white/[6%] hover:text-[#e8eef8]" aria-label="Schließen">
            <X size={16} />
          </button>
        </header>

        <main className="min-h-0 flex-1 overflow-y-auto p-4">{children}</main>

        {footer && (
          <footer className="flex shrink-0 items-center gap-2 border-t border-[#2a364b] bg-[#0b111c] px-4 py-3">
            {footer}
          </footer>
        )}
      </div>
    </div>
  )
}
