import type { CSSProperties } from "react"
import { useEffect, useState } from "react"
import { Activity, AlertCircle, Clock, Zap } from "lucide-react"
import { useTranslation } from "react-i18next"
import { rgbFor } from "@/shared/colors"
import { llmApi, type AnthropicRateLimits } from "./api"

export function AnthropicUsageCard() {
  const { t } = useTranslation("llm")
  const [limits, setLimits] = useState<AnthropicRateLimits | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadLimits()
    const interval = setInterval(loadLimits, 60000) // Refresh every minute
    return () => clearInterval(interval)
  }, [])

  async function loadLimits() {
    try {
      const data = await llmApi.getAnthropicRateLimits()
      setLimits(data)
    } catch {
      setLimits(null)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-4">
        <div className="flex items-center gap-2 text-sm text-zinc-500">
          <Activity size={16} className="animate-pulse" />
          {t("usage.loading")}
        </div>
      </div>
    )
  }

  if (!limits || !limits.updated_at) {
    return null // No data yet
  }

  const util5h = limits["5h_utilization"] ?? 0
  const util7d = limits["7d_utilization"] ?? 0
  const hasData = util5h > 0 || util7d > 0

  if (!hasData) return null

  const getColor = (util: number) => {
    if (util >= 0.9) return "text-red-400 bg-red-500/10 border-red-500/30"
    if (util >= 0.7) return "text-amber-400 bg-amber-500/10 border-amber-500/30"
    return "text-emerald-400 bg-emerald-500/10 border-emerald-500/30"
  }

  const getBarColor = (util: number) => {
    if (util >= 0.9) return "bg-red-500"
    if (util >= 0.7) return "bg-amber-500"
    return "bg-emerald-500"
  }

  return (
    <div className="box overflow-hidden p-4 space-y-3" style={{ "--c": rgbFor("/llm") } as CSSProperties}>
      <div className="flex items-center gap-2 text-sm font-medium text-violet-300">
        <Zap size={16} />
        {t("usage.anthropic_title")}
      </div>

      {/* 5-Hour Window */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-zinc-400">{t("usage.window_5h")}</span>
          <span className={`px-2 py-0.5 rounded ${getColor(util5h)} text-xs font-medium`}>
            {(util5h * 100).toFixed(1)}%
          </span>
        </div>
        <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${getBarColor(util5h)}`}
            style={{ width: `${util5h * 100}%` }}
          />
        </div>
        {limits["5h_reset"] && (
          <div className="flex items-center gap-1 text-[10px] text-zinc-500">
            <Clock size={10} />
            {t("usage.resets_at")}: {new Date(limits["5h_reset"]).toLocaleString()}
          </div>
        )}
      </div>

      {/* 7-Day Window */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-zinc-400">{t("usage.window_7d")}</span>
          <span className={`px-2 py-0.5 rounded ${getColor(util7d)} text-xs font-medium`}>
            {(util7d * 100).toFixed(1)}%
          </span>
        </div>
        <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${getBarColor(util7d)}`}
            style={{ width: `${util7d * 100}%` }}
          />
        </div>
        {limits["7d_reset"] && (
          <div className="flex items-center gap-1 text-[10px] text-zinc-500">
            <Clock size={10} />
            {t("usage.resets_at")}: {new Date(limits["7d_reset"]).toLocaleString()}
          </div>
        )}
      </div>

      {/* Warning if threshold surpassed */}
      {(limits["5h_surpassed_threshold"] || limits["7d_surpassed_threshold"]) && (
        <div className="flex items-start gap-2 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded p-2 mt-2">
          <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
          <div>
            <div className="font-medium">{t("usage.threshold_warning")}</div>
            <div className="text-[10px] text-amber-400/70 mt-0.5">
              {t("usage.threshold_explanation")}
            </div>
          </div>
        </div>
      )}

      {/* Overage Status */}
      {limits.overage_status && (
        <div className="text-[10px] text-zinc-500 pt-1 border-t border-zinc-800">
          Overage: {limits.overage_status}
          {limits.overage_utilization !== undefined && ` (${(limits.overage_utilization * 100).toFixed(1)}%)`}
        </div>
      )}
    </div>
  )
}
