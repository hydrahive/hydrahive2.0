import type { ReactNode } from "react"
import { cn } from "@/shared/cn"
import { BoxHead } from "@/shared/brand/BoxHead"
import { BoxStatusSchild } from "@/shared/brand/BoxStatus"
import { boxLook, boxRahmenStil, kopfTonStil, type BoxStatus } from "@/shared/brand/boxLook"
import type { BoxTheme } from "@/shared/brand/boxThemes"

interface Props {
  title?: string
  eyebrow?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
  /** Thema der Box: fester Hydra-Kopf im Kopf + Streifen links in dessen Farbe. */
  theme?: BoxTheme
  /** Zustand: Warnung/Fehler übermalen die Kopffarbe (gelb/rot), „ok“ zeigt nur das Schild. */
  status?: BoxStatus
  /** Klassen für den Inhaltsbereich (z. B. Spalten-Layout mit scrollender Liste). */
  bodyClassName?: string
  /** Inhalt ohne Innenabstand (z. B. Dateibaum bis an den Rand). */
  flush?: boolean
}

/** Cockpit-Box. Flächen aus den Farbstufen (index.css), Farbe aus boxLook (Plan farbstufen-kopffarben). */
export function CockpitPanel({ title, eyebrow, actions, children, className, theme, status, bodyClassName, flush }: Props) {
  const look = boxLook(theme, status)
  const hatKopf = Boolean(title || eyebrow || actions || theme || status)
  return (
    <section data-box-theme={theme} style={boxRahmenStil(look)}
      className={cn("flex min-h-0 flex-col overflow-hidden rounded-[6px] border border-s-rand bg-s-box text-[#e8eef8]", className)}>
      {hatKopf && (
        <header style={kopfTonStil(look)}
          className="flex shrink-0 items-center justify-between gap-3 border-b border-s-rand bg-s-kopf px-3 py-2">
          <div className="flex min-w-0 items-center gap-2.5">
            {theme && <BoxHead theme={theme} />}
            <div className="min-w-0">
              {eyebrow && <CockpitSectionLabel farbe={look.streifen}>{eyebrow}</CockpitSectionLabel>}
              {title && <h2 className="truncate text-sm font-bold text-[#e8eef8]">{title}</h2>}
            </div>
          </div>
          {(look.schild || actions) && (
            <div className="flex shrink-0 items-center gap-2">
              {look.schild && <BoxStatusSchild status={look.schild} />}
              {actions}
            </div>
          )}
        </header>
      )}
      <div className={cn("min-h-0 flex-1", !flush && "p-3", bodyClassName)}>{children}</div>
    </section>
  )
}

/** Kleines Etikett über dem Titel; in einer Box mit Kopffarbe trägt es deren Farbe. */
export function CockpitSectionLabel({ children, farbe }: { children: ReactNode; farbe?: string | null }) {
  if (farbe) {
    return (
      <p className="mb-0.5 text-[10px] font-black uppercase tracking-[0.14em]" style={{ color: farbe }}>
        {children}
      </p>
    )
  }
  return (
    <p className="mb-1 inline-flex rounded-[4px] border border-[#69d7ff]/35 bg-[#1c2940] px-2 py-1 text-[10px] font-black uppercase tracking-[0.14em] text-[#69d7ff]">
      {children}
    </p>
  )
}
