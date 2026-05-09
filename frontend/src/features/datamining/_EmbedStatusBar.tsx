interface EmbedStatus {
  active: boolean
  total: number
  embedded: number
  pending: number
  model: string
  backfill_running: boolean
}

export function EmbedStatusBar({ status, onBackfill, onReset }: {
  status: EmbedStatus
  onBackfill: () => void
  onReset: () => void
}) {
  const pct = status.total > 0 ? Math.round((status.embedded / status.total) * 100) : 0
  const allDone = status.pending === 0 && status.total > 0

  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/[2%] border border-white/[6%] text-xs">
      <span className="text-zinc-500 shrink-0">{status.model || "—"}</span>
      <div className="flex-1 h-1 bg-white/[8%] rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${allDone ? "bg-emerald-500" : "bg-violet-500"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-zinc-500 shrink-0 tabular-nums">
        {status.embedded}/{status.total}
      </span>
      {status.backfill_running ? (
        <span className="text-violet-400 shrink-0 animate-pulse">einbettend…</span>
      ) : status.pending > 0 ? (
        <button onClick={onBackfill} className="text-violet-400 hover:text-violet-300 shrink-0 transition-colors">
          backfill
        </button>
      ) : null}
      <button onClick={onReset} className="text-zinc-600 hover:text-zinc-400 shrink-0 transition-colors" title="Alle Embeddings zurücksetzen">
        ↺
      </button>
    </div>
  )
}

export type { EmbedStatus }
