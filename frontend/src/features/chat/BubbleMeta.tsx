import { useTranslation } from "react-i18next"
import { estimateCostUsd, formatCost } from "./pricing"

function formatBubbleTime(iso: string, locale: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ""
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  const yesterday = new Date(now); yesterday.setDate(now.getDate() - 1)
  const isYesterday = d.toDateString() === yesterday.toDateString()
  const time = d.toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" })
  const dayLabel = sameDay
    ? i18nToday(locale)
    : isYesterday
      ? i18nYesterday(locale)
      : d.toLocaleDateString(locale, { day: "2-digit", month: "2-digit", year: "numeric" })
  return `${dayLabel} · ${time}`
}

function i18nYesterday(locale: string): string {
  return locale.startsWith("de") ? "Gestern" : "Yesterday"
}

function i18nToday(locale: string): string {
  return locale.startsWith("de") ? "Heute" : "Today"
}

export function BubbleHeader({ createdAt, align }: { createdAt: string; align: "left" | "right" }) {
  const { i18n } = useTranslation()
  const text = formatBubbleTime(createdAt, i18n.language)
  if (!text) return null
  return (
    <div className={`text-[10px] text-zinc-500/70 tabular-nums ${align === "right" ? "text-right" : "text-left"}`}>
      {text}
    </div>
  )
}

interface AssistantMeta {
  input_tokens?: number
  output_tokens?: number
  cache_creation_tokens?: number
  cache_read_tokens?: number
  model?: string
  iteration?: number
  stop_reason?: string
}

export function AssistantFooter({ metadata }: { metadata?: Record<string, unknown> }) {
  const { t, i18n } = useTranslation("chat")
  const meta = (metadata ?? {}) as AssistantMeta
  const fmt = (n?: number) => n != null ? n.toLocaleString(i18n.language) : "—"
  const hasTokens = meta.input_tokens || meta.output_tokens
  const hasCache = meta.cache_creation_tokens || meta.cache_read_tokens
  const hasModel = !!meta.model
  const showIterations = meta.iteration != null && meta.iteration > 1
  const showStopReason = !!meta.stop_reason && meta.stop_reason !== "end_turn"
  const costUsd = estimateCostUsd(meta.model, {
    input: meta.input_tokens,
    output: meta.output_tokens,
    cache_read: meta.cache_read_tokens,
    cache_creation: meta.cache_creation_tokens,
  })
  if (!hasTokens && !hasModel) return null
  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px] text-zinc-500/70 font-mono tabular-nums">
      {hasTokens && (
        <span>{t("bubble_footer.tokens", { in: fmt(meta.input_tokens), out: fmt(meta.output_tokens) })}</span>
      )}
      {hasCache && (
        <span>· {t("bubble_footer.cache", { read: fmt(meta.cache_read_tokens), create: fmt(meta.cache_creation_tokens) })}</span>
      )}
      {costUsd != null && (
        <span className="text-emerald-400/70" title={t("bubble_footer.cost_tooltip")}>
          · {formatCost(costUsd, i18n.language)}
        </span>
      )}
      {hasModel && (
        <span className="text-zinc-500/90">· {meta.model}</span>
      )}
      {showIterations && (
        <span>· {t("bubble_footer.iterations", { n: meta.iteration })}</span>
      )}
      {showStopReason && (
        <span className="text-amber-400/70">· {t("bubble_footer.stop_reason", { reason: meta.stop_reason })}</span>
      )}
    </div>
  )
}
