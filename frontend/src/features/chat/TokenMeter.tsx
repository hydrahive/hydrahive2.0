import { useEffect, useState } from "react"
import { chatApi } from "./api"

interface Props {
  sessionId: string
  /** Bumping this number triggers a re-fetch (e.g. after a message was sent). */
  refresh: number
}

interface TokenInfo {
  used: number
  context_window: number
  compact_threshold: number
}

export function TokenMeter({ sessionId, refresh }: Props) {
  const [info, setInfo] = useState<TokenInfo | null>(null)

  useEffect(() => {
    chatApi.tokens(sessionId).then(setInfo).catch(() => setInfo(null))
  }, [sessionId, refresh])

  if (!info || info.context_window === 0) return null

  const pct = info.compact_threshold > 0 ? Math.min(100, (info.used / info.compact_threshold) * 100) : 0
  const tone =
    pct < 50 ? "text-zinc-500"
      : pct < 80 ? "text-amber-400"
      : "text-rose-400"
  const barTone =
    pct < 50 ? "bg-zinc-600"
      : pct < 80 ? "bg-amber-400"
      : "bg-rose-400"

  return (
    <div className="flex items-center gap-2" title={`Compact-Schwelle bei ${info.compact_threshold.toLocaleString("de")} Tokens`}>
      <div className="w-20 h-1 bg-white/[6%] rounded-full overflow-hidden">
        <div className={`h-full ${barTone} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-[11px] font-mono tabular-nums ${tone}`}>
        {info.used.toLocaleString("de")} / {(info.compact_threshold).toLocaleString("de")}
      </span>
    </div>
  )
}
