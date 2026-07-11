import { useEffect, useState } from "react"
import { api } from "@/shared/api-client"
import {
  llmApi,
  type AnthropicRateLimits,
  type CodexUsage,
  type OpenRouterCredits,
} from "@/features/llm/api"

const REFRESH_MS = 60_000

interface MinimaxModel {
  label: string
  category: string
  weekly_total: number
  weekly_used: number
  weekly_pct: number
  interval_reset_in_s: number
}
interface MinimaxUsage {
  available: boolean
  reason?: string
  models?: MinimaxModel[]
}

function fmtResetIn(s: number): string {
  if (s <= 0) return "—"
  const d = Math.floor(s / 86400)
  if (d > 0) return `${d}d ${Math.floor((s % 86400) / 3600)}h`
  const h = Math.floor(s / 3600)
  if (h > 0) return `${h}h ${Math.floor((s % 3600) / 60)}m`
  return `${Math.max(1, Math.floor(s / 60))}m`
}

function barTone(pct: number): string {
  if (pct >= 90) return "bg-rose-400"
  if (pct >= 70) return "bg-amber-400"
  return "bg-emerald-400"
}

/** Eine kompakte Balken-Zeile: Label · %-Balken · Reset/Zahl rechts. */
function UsageBar({ label, pct, right }: { label: string; pct: number; right?: string }) {
  const clamped = Math.max(0, Math.min(100, pct))
  return (
    <div className="flex items-center gap-2">
      <span className="w-9 shrink-0 text-[10px] font-semibold uppercase tracking-wide text-[#8d9ab0]">{label}</span>
      <div className="relative h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-white/[6%]">
        <div className={`absolute inset-y-0 left-0 rounded-full ${barTone(clamped)}`} style={{ width: `${clamped}%` }} />
      </div>
      <span className="w-7 shrink-0 text-right text-[10px] tabular-nums text-[#c3ccdd]">{Math.round(clamped)}%</span>
      {right !== undefined ? (
        <span className="w-14 shrink-0 text-right text-[9px] tabular-nums text-[#7a869c]">{right}</span>
      ) : null}
    </div>
  )
}

function ProviderBlock({ name, children }: { name: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <p className="text-[9px] font-black uppercase tracking-[0.12em] text-[#5f6d84]">{name}</p>
      {children}
    </div>
  )
}

export function CockpitUsagePanel() {
  const [anthropic, setAnthropic] = useState<AnthropicRateLimits | null>(null)
  const [codex, setCodex] = useState<CodexUsage | null>(null)
  const [minimax, setMinimax] = useState<MinimaxUsage | null>(null)
  const [openrouter, setOpenrouter] = useState<OpenRouterCredits | null>(null)

  useEffect(() => {
    let alive = true
    async function load() {
      const [a, c, m, o] = await Promise.allSettled([
        llmApi.getAnthropicRateLimits(),
        llmApi.getCodexUsage(),
        api.get<MinimaxUsage>("/llm/minimax/usage"),
        llmApi.getOpenRouterCredits(),
      ])
      if (!alive) return
      if (a.status === "fulfilled") setAnthropic(a.value)
      if (c.status === "fulfilled") setCodex(c.value)
      if (m.status === "fulfilled") setMinimax(m.value)
      if (o.status === "fulfilled") setOpenrouter(o.value)
    }
    void load()
    const id = setInterval(() => void load(), REFRESH_MS)
    return () => { alive = false; clearInterval(id) }
  }, [])

  // Anthropic nur wenn echte Utilization-Daten vorliegen.
  const aUtil5h = anthropic?.["5h_utilization"] ?? 0
  const aUtil7d = anthropic?.["7d_utilization"] ?? 0
  const showAnthropic = Boolean(anthropic?.updated_at) && (aUtil5h > 0 || aUtil7d > 0)

  const showCodex = Boolean(codex?.available) && Boolean(codex?.primary || codex?.secondary)
  const showOpenrouter = Boolean(openrouter?.available)
  const minimaxModels = (minimax?.available ? minimax.models ?? [] : []).filter((m) => m.weekly_total > 0)
  const showMinimax = minimaxModels.length > 0

  const anyActive = showAnthropic || showCodex || showOpenrouter || showMinimax

  return (
    <div className="space-y-3">
      {!anyActive ? (
        <p className="text-xs text-[#7a869c]">Keine aktive Modellquelle mit Verbrauchsdaten.</p>
      ) : null}

      {showAnthropic ? (
        <ProviderBlock name="Anthropic">
          {aUtil5h > 0 ? <UsageBar label="5h" pct={aUtil5h * 100} right={fmtResetIn(secondsUntil(anthropic?.["5h_reset"]))} /> : null}
          {aUtil7d > 0 ? <UsageBar label="7d" pct={aUtil7d * 100} right={fmtResetIn(secondsUntil(anthropic?.["7d_reset"]))} /> : null}
        </ProviderBlock>
      ) : null}

      {showCodex ? (
        <ProviderBlock name={`Codex${codex?.plan_type ? ` · ${codex.plan_type}` : ""}`}>
          {codex?.primary ? <UsageBar label="5h" pct={codex.primary.used_pct} right={fmtResetIn(codex.primary.reset_in_s)} /> : null}
          {codex?.secondary ? <UsageBar label="7d" pct={codex.secondary.used_pct} right={fmtResetIn(codex.secondary.reset_in_s)} /> : null}
        </ProviderBlock>
      ) : null}

      {showOpenrouter ? (
        <ProviderBlock name="OpenRouter">
          <UsageBar
            label="Rest"
            pct={openrouter?.used_pct ?? 0}
            right={`$${(openrouter?.remaining ?? 0).toFixed(2)}`}
          />
        </ProviderBlock>
      ) : null}

      {showMinimax ? (
        <ProviderBlock name="MiniMax">
          {minimaxModels.map((m) => (
            <UsageBar key={m.label} label={m.category.slice(0, 4)} pct={m.weekly_pct} right={fmtResetIn(m.interval_reset_in_s)} />
          ))}
        </ProviderBlock>
      ) : null}
    </div>
  )
}

/** ISO-Reset-Zeitpunkt → Sekunden ab jetzt (Anthropic liefert absolute Zeit). */
function secondsUntil(iso?: string): number {
  if (!iso) return 0
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return 0
  return Math.max(0, Math.floor((t - Date.now()) / 1000))
}
