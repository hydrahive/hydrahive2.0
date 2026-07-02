import type { ReactNode } from "react"

/** Höhen-Wrapper für Seiten-Bausteine, die ihren Container voll ausfüllen wollen
 *  (h-full — z.B. Chat-Seiten). Im Template-Fluss gibt es keine natürliche Höhe,
 *  daher spannt dieser Wrapper einen definierten Kasten auf.
 *
 *  height-Attribut vom Tag (regex-validiert), Default 70vh. Bausteine ohne
 *  Höhenbedarf (Listen etc.) können full={false} nutzen → natürliche Höhe. */
export function PageBlock({
  attrs, children, full = true,
}: { attrs: Record<string, string>; children: ReactNode; full?: boolean }) {
  if (!full) return <div className="min-h-[200px]">{children}</div>
  const height = attrs.height && /^[0-9]+(px|vh|rem|%)$/.test(attrs.height) ? attrs.height : "70vh"
  return (
    <div style={{ height }} className="min-h-[320px]">
      {children}
    </div>
  )
}
