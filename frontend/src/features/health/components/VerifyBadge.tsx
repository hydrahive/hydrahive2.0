import { useTranslation } from "react-i18next"

interface Props {
  verifiziert: number
  onVerify?: () => void
}

export function VerifyBadge({ verifiziert, onVerify }: Props) {
  const { t } = useTranslation("health")
  if (verifiziert) {
    return (
      <span title={t("akte.verified_title")} className="text-emerald-400 cursor-default">●</span>
    )
  }
  return (
    <span
      title={t("akte.unverified_title")}
      className="text-orange-400 cursor-pointer hover:text-orange-300"
      role="button"
      onClick={onVerify}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onVerify?.() }}
      tabIndex={0}
    >
      ●
    </span>
  )
}
