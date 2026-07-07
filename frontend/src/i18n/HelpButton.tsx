import { HelpCircle } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { HelpDrawer } from "./HelpDrawer"
import type { HelpTopic } from "./help/loader"

interface Props {
  topic: HelpTopic
  className?: string
  /** Auffällige Variante: Icon + Label "Hilfe", kräftiges Violett mit Border. */
  prominent?: boolean
}

export function HelpButton({ topic, className = "", prominent = false }: Props) {
  const [open, setOpen] = useState(false)
  const { t } = useTranslation("nav")
  return (
    <>
      <button
        onClick={() => setOpen(true)}
        title={t("help_button")}
        className={
          prominent
            ? `${className} inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium text-violet-200 bg-violet-500/15 hover:bg-violet-500/25 border border-violet-500/40 transition-colors`.trim()
            : `${className} p-2 rounded-lg text-zinc-500 hover:text-violet-300 hover:bg-violet-500/10 transition-colors`.trim()
        }
      >
        <HelpCircle size={prominent ? 14 : 15} />
        {prominent && <span>{t("help_label")}</span>}
      </button>
      <HelpDrawer topic={topic} open={open} onClose={() => setOpen(false)} />
    </>
  )
}
