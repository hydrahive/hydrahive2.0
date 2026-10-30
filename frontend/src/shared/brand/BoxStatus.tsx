import { AlertTriangle, CheckCircle2, XOctagon } from "lucide-react"
import { useTranslation } from "react-i18next"
import { STATUS_FARBE, type BoxStatus } from "./boxLook"

const SYMBOL = { warnung: AlertTriangle, fehler: XOctagon, ok: CheckCircle2 } as const

/** Schild oben rechts in einer Box: Symbol + Wort, nie nur Farbe (Plan farbstufen-kopffarben, Task 2). */
export function BoxStatusSchild({ status }: { status: BoxStatus }) {
  const { t } = useTranslation("common")
  const Symbol = SYMBOL[status]
  const f = STATUS_FARBE[status]
  return (
    <span data-box-status={status}
      className="inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-bold"
      style={{ color: f, borderColor: `${f}66`, backgroundColor: `${f}1a` }}>
      <Symbol size={12} aria-hidden="true" />
      {t(`boxStatus.${status}`)}
    </span>
  )
}
