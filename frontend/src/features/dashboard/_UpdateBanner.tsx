import { ArrowUp, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"

interface Props {
  behind: number
  onDismiss?: () => void
}

export function UpdateBanner({ behind, onDismiss }: Props) {
  const { t } = useTranslation("dashboard")
  const role = useAuthStore((s) => s.role)
  return (
    <div className="flex items-center gap-3 rounded-xl border border-amber-500/25 bg-amber-500/[6%] px-4 py-2.5">
      <ArrowUp size={14} className="text-amber-300 flex-shrink-0" />
      <p className="text-xs text-amber-200 flex-1">
        {t("update_banner.text", { count: behind })}
      </p>
      {role === "admin" && (
        <a href="/system" className="text-xs text-amber-200 hover:text-amber-100 underline">
          {t("update_banner.go")}
        </a>
      )}
      {onDismiss && (
        <button onClick={onDismiss} className="p-1 rounded text-amber-300/60 hover:text-amber-200 hover:bg-amber-500/10">
          <X size={11} />
        </button>
      )}
    </div>
  )
}
