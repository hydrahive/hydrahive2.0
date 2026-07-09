import { Activity, CircleDollarSign, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { estimateCostUsd, formatCost } from "@/features/chat/pricing"
import type { LlmProviderId } from "./api"

type LastTurnTokens = {
  input: number
  output: number
  cache_creation: number
  cache_read: number
} | null

function providerLabel(provider: LlmProviderId | null | undefined) {
  if (!provider || provider === "unknown") return "unknown"
  return String(provider)
}

export function BuddyUsageChip({
  model,
  provider,
  lastTurnTokens,
  busy,
}: {
  model?: string
  provider?: LlmProviderId | null
  lastTurnTokens: LastTurnTokens
  busy: boolean
  sessionId?: string
}) {
  const { t, i18n } = useTranslation("buddy")
  const total = lastTurnTokens
    ? lastTurnTokens.input + lastTurnTokens.output + lastTurnTokens.cache_creation + lastTurnTokens.cache_read
    : null
  const cost = lastTurnTokens ? estimateCostUsd(model, lastTurnTokens) : null
  const fmt = (n: number) => n.toLocaleString(i18n.language)

  return (
    <div
      className="flex max-w-full items-center gap-2 border border-white/[8%] bg-black/25 px-2.5 py-1 text-[11px] text-zinc-400 shadow-inner shadow-black/20"
      title={model ? `${providerLabel(provider)} · ${model}` : providerLabel(provider)}
    >
      {busy ? <Loader2 size={12} className="animate-spin text-sky-300" /> : <Activity size={12} className="text-sky-300" />}
      <span className="font-mono uppercase tracking-wide text-zinc-300">{providerLabel(provider)}</span>
      <span className="h-3 w-px bg-white/[10%]" />
      {total == null ? (
        <span>{t("cockpit.usage.no_turn")}</span>
      ) : (
        <span className="font-mono tabular-nums text-zinc-300">{fmt(total)} tok</span>
      )}
      {lastTurnTokens && lastTurnTokens.cache_read > 0 && (
        <span className="text-emerald-300/80">r:{fmt(lastTurnTokens.cache_read)}</span>
      )}
      {lastTurnTokens && lastTurnTokens.cache_creation > 0 && (
        <span className="text-amber-300/80">w:{fmt(lastTurnTokens.cache_creation)}</span>
      )}
      <span className="h-3 w-px bg-white/[10%]" />
      <CircleDollarSign size={11} className="text-zinc-500" />
      <span className={cost == null ? "text-zinc-500" : "font-mono tabular-nums text-zinc-300"}>
        {cost == null ? t("cockpit.usage.price_na") : formatCost(cost, i18n.language)}
      </span>
    </div>
  )
}
