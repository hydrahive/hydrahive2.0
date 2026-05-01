import { useTranslation } from "react-i18next"

export function BuddyPage() {
  const { t } = useTranslation("buddy")
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
      <div className="text-7xl">🐝</div>
      <h1 className="text-2xl font-bold text-zinc-100">{t("title")}</h1>
      <p className="text-sm text-zinc-500 max-w-md text-center">{t("placeholder")}</p>
      <p className="text-[11px] text-zinc-600">{t("coming_soon")}</p>
    </div>
  )
}
