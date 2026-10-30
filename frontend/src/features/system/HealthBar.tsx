import { CheckCircle, XCircle } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminStatus } from "@/features/cockpit/admin/ui"
import type { HealthCheck } from "./api"

export function HealthBar({ checks }: { checks: HealthCheck[] }) {
  const { t } = useTranslation("system")
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {checks.map((check, index) => {
        const name = check.name_code ? t(`checks.${check.name_code}`) : (check.name ?? "?")
        const detail = check.detail_code ? t(`checks.${check.detail_code}`, check.params ?? {}) : (check.detail ?? "")
        return (
          <div key={check.name_code ?? check.name ?? index} className="rounded-[6px] border border-s-rand bg-s-innen p-3">
            <AdminStatus tone={check.ok ? "success" : "danger"} icon={check.ok ? CheckCircle : XCircle}>
              {name}
            </AdminStatus>
            <p className="mt-2 break-words text-xs leading-relaxed text-[#9aa7bc]" title={detail}>{detail}</p>
          </div>
        )
      })}
    </div>
  )
}
