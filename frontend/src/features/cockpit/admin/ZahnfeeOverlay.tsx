import { useTranslation } from "react-i18next"
import { ZahnfeeConfig } from "@/features/zahnfee/ZahnfeeConfig"
import { AdminOverlay } from "./AdminOverlay"

/** Zahnfee-Einstellungen im Admin-Cockpit (/admin?section=zahnfee). Die Auswertung bleibt auf /zahnfee. */
export function ZahnfeeOverlay({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("zahnfee")
  return (
    <AdminOverlay eyebrow="Admin" title={`Zahnfee · ${t("config.title")}`} onClose={onClose} maxWidthClass="max-w-3xl">
      <ZahnfeeConfig />
    </AdminOverlay>
  )
}
