import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Pickaxe } from "lucide-react"
import { LiveFeedTab } from "./LiveFeedTab"
import { SearchTab } from "./SearchTab"
import { SessionsTab } from "./SessionsTab"
import { dataminingApi } from "./api"

const TABS = ["feed", "search", "sessions"] as const
type Tab = typeof TABS[number]

interface EmbedStatus {
  active: boolean
  total: number
  embedded: number
  pending: number
  model: string
  backfill_running: boolean
}

export function DataminingPage() {
  const { t } = useTranslation("datamining")
  const [tab, setTab] = useState<Tab>("feed")
  const [embedStatus, setEmbedStatus] = useState<EmbedStatus | null>(null)

  useEffect(() => {
    dataminingApi.embedStatus().then(setEmbedStatus).catch(() => {})
    const iv = setInterval(() => {
      dataminingApi.embedStatus().then(setEmbedStatus).catch(() => {})
    }, 8000)
    return () => clearInterval(iv)
  }, [])

  return (
    <div className="space-y-4 max-w-4xl">
      <div className="flex items-center gap-3">
        <Pickaxe className="text-amber-400" size={20} />
        <div>
          <h1 className="text-xl font-semibold text-zinc-100">{t("title")}</h1>
          <p className="text-xs text-zinc-500 mt-0.5">{t("subtitle")}</p>
        </div>
      </div>

      <div className="flex gap-1 border-b border-white/[6%]">
        {TABS.map((id) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === id
                ? "text-amber-300 border-amber-400"
                : "text-zinc-500 border-transparent hover:text-zinc-300"
            }`}
          >
            {t(`tabs.${id}`)}
          </button>
        ))}
      </div>

      {embedStatus?.active && (
        <EmbedStatusBar status={embedStatus} onBackfill={() =>
          dataminingApi.triggerBackfill()
            .then(() => dataminingApi.embedStatus().then(setEmbedStatus).catch(() => {}))
            .catch(() => {})
        } />
      )}

      {tab === "feed" && <LiveFeedTab active={tab === "feed"} />}
      {tab === "search" && <SearchTab />}
      {tab === "sessions" && <SessionsTab active={tab === "sessions"} />}
    </div>
  )
}

function EmbedStatusBar({ status, onBackfill }: { status: EmbedStatus; onBackfill: () => void }) {
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
        <button
          onClick={onBackfill}
          className="text-violet-400 hover:text-violet-300 shrink-0 transition-colors"
        >
          backfill
        </button>
      ) : null}
    </div>
  )
}
