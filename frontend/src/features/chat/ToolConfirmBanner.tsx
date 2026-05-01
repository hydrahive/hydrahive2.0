import { Check, ShieldAlert, X } from "lucide-react"
import { useTranslation } from "react-i18next"

export interface PendingConfirm {
  call_id: string
  tool_name: string
  arguments: Record<string, unknown>
}

interface Props {
  pending: PendingConfirm
  onApprove: () => void
  onDeny: () => void
  busy?: boolean
}

export function ToolConfirmBanner({ pending, onApprove, onDeny, busy }: Props) {
  const { t } = useTranslation("chat")
  const argsStr = JSON.stringify(pending.arguments, null, 0)
  const argsShort = argsStr.length > 200 ? argsStr.slice(0, 197) + "…" : argsStr

  return (
    <div className="mx-6 mt-3 px-4 py-3 rounded-lg border border-amber-500/40 bg-amber-500/[8%] flex items-start gap-3">
      <ShieldAlert size={16} className="text-amber-300 flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0 space-y-1">
        <p className="text-sm text-amber-100">
          {t("tool_confirm.message")}
          {" "}
          <code className="font-mono text-amber-200 bg-amber-500/10 px-1.5 py-0.5 rounded">{pending.tool_name}</code>
        </p>
        <p className="text-[11px] font-mono text-amber-200/70 truncate" title={argsStr}>
          {argsShort}
        </p>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <button
          onClick={onDeny}
          disabled={busy}
          className="flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs text-rose-300 hover:bg-rose-500/15 border border-rose-500/30 disabled:opacity-40 transition-colors"
        >
          <X size={12} /> {t("tool_confirm.deny")}
        </button>
        <button
          onClick={onApprove}
          disabled={busy}
          className="flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs text-emerald-100 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 disabled:opacity-40 transition-colors"
        >
          <Check size={12} /> {t("tool_confirm.approve")}
        </button>
      </div>
    </div>
  )
}
