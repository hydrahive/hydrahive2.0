import { useTranslation } from "react-i18next"
import { ZahnfeeConfig } from "@/features/zahnfee/ZahnfeeConfig"
import { AdminOverlay } from "./AdminOverlay"
import { ADMIN_OVERLAY_THEME } from "@/shared/brand/boxThemes"

/** Zahnfee-Einstellungen im Admin-Cockpit (/admin?section=zahnfee). Die Auswertung bleibt auf /zahnfee. */
export function ZahnfeeOverlay({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("zahnfee")
  return (
    <AdminOverlay theme={ADMIN_OVERLAY_THEME["zahnfee"]} eyebrow="Admin" title={`Zahnfee · ${t("config.title")}`} onClose={onClose} maxWidthClass="max-w-3xl">
      <ZahnfeeConfig />
    </AdminOverlay>
  )
}
