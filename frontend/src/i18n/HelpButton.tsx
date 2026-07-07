import { HelpCircle } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { HelpDrawer } from "./HelpDrawer"
import type { HelpTopic } from "./help/loader"

interface Props {
  topic: HelpTopic
  className?: string
}

/** Auffälliger gelber "Hilfe"-Blob — öffnet die Seiten-Hilfe im Drawer. */
export function HelpButton({ topic, className = "" }: Props) {
  const [open, setOpen] = useState(false)
  const { t } = useTranslation("nav")
  return (
    <>
      <button
        onClick={() => setOpen(true)}
        title={t("help_button")}
        className={`${className} inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold text-amber-950 bg-amber-400 hover:bg-amber-300 border border-amber-500/60 shadow-sm shadow-amber-500/20 transition-colors`.trim()}
      >
        <HelpCircle size={14} />
        <span>{t("help_label")}</span>
      </button>
      <HelpDrawer topic={topic} open={open} onClose={() => setOpen(false)} />
    </>
  )
}
