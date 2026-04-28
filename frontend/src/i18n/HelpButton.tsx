import { HelpCircle } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { HelpDrawer } from "./HelpDrawer"
import type { HelpTopic } from "./help/loader"

export function HelpButton({ topic }: { topic: HelpTopic }) {
  const [open, setOpen] = useState(false)
  const { t } = useTranslation("nav")
  return (
    <>
      <button
        onClick={() => setOpen(true)}
        title={t("help_button")}
        className="p-2 rounded-lg text-zinc-500 hover:text-violet-300 hover:bg-violet-500/10 transition-colors"
      >
        <HelpCircle size={15} />
      </button>
      <HelpDrawer topic={topic} open={open} onClose={() => setOpen(false)} />
    </>
  )
}
