import { HelpCircle } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { adminActionClass } from "@/features/cockpit/admin/ui"
import { HelpDrawer } from "./HelpDrawer"
import type { HelpTopic } from "./help/loader"

interface Props {
  topic: HelpTopic
  className?: string
}

export function HelpButton({ topic, className }: Props) {
  const [open, setOpen] = useState(false)
  const { t } = useTranslation("nav")
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        title={t("help_button")}
        className={adminActionClass("default", className)}
      >
        <HelpCircle size={14} />
        <span>{t("help_label")}</span>
      </button>
      <HelpDrawer topic={topic} open={open} onClose={() => setOpen(false)} />
    </>
  )
}
