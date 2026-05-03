import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Download, Pickaxe, Upload } from "lucide-react"
import { LiveFeedTab } from "./LiveFeedTab"
import { SearchTab } from "./SearchTab"
import { SessionsTab } from "./SessionsTab"
import { GraphTab } from "./GraphTab"
import { dataminingApi } from "./api"

const TABS = ["feed", "search", "sessions", "graph"] as const
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
  const [exportState, setExportState] = useState<"idle" | "running" | "done" | "error">("idle")
  const [exportFile, setExportFile] = useState<string | null>(null)
  const [exportSizeMb, setExportSizeMb] = useState<number>(0)
  const [importState, setImportState] = useState<"idle" | "running" | "done" | "error">("idle")
  const importRef = useRef<HTMLInputElement>(null)
  const [sqliteImport, setSqliteImport] = useState<{ running: boolean; sessions: number; total: number } | null>(null)

  useEffect(() => {
    dataminingApi.embedStatus().then(setEmbedStatus).catch(() => {})
    const iv = setInterval(() => {
      dataminingApi.embedStatus().then(setEmbedStatus).catch(() => {})
    }, 8000)
    dataminingApi.exportStatus().then((s) => {
      if (s.done && s.filename) { setExportState("done"); setExportFile(s.filename); setExportSizeMb(s.size_mb) }
    }).catch(() => {})
    dataminingApi.importStatus().then((s) => {
      if (s.running) setImportState("running")
    }).catch(() => {})
    dataminingApi.sqliteImportStatus().then((s) => {
      if (s.running) setSqliteImport({ running: true, sessions: s.sessions, total: s.total_sessions })
    }).catch(() => {})
    return () => clearInterval(iv)
  }, [])

  async function startExport() {
    setExportState("running"); setExportFile(null)
    await dataminingApi.startExport().catch(() => {})
    const poll = setInterval(async () => {
      const s = await dataminingApi.exportStatus().catch(() => null)
      if (!s) return
      if (s.done) {
        setExportState("done"); setExportFile(s.filename); setExportSizeMb(s.size_mb)
        clearInterval(poll)
      } else if (s.error) {
        setExportState("error"); clearInterval(poll)
      }
    }, 2000)
  }

  async function handleImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]; if (!file) return
    setImportState("running")
    await dataminingApi.startImport(file).catch(() => { setImportState("error"); return })
    const poll = setInterval(async () => {
      const s = await dataminingApi.importStatus().catch(() => null)
      if (!s) return
      if (s.done) { setImportState("done"); clearInterval(poll) }
      else if (s.error) { setImportState("error"); clearInterval(poll) }
    }, 2000)
  }

  async function startSqliteImport() {
    await dataminingApi.startSqliteImport().catch(() => {})
    setSqliteImport({ running: true, sessions: 0, total: 0 })
    const poll = setInterval(async () => {
      const s = await dataminingApi.sqliteImportStatus().catch(() => null)
      if (!s) return
      setSqliteImport({ running: s.running, sessions: s.sessions, total: s.total_sessions })
      if (!s.running) clearInterval(poll)
    }, 2000)
  }

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
        <EmbedStatusBar
          status={embedStatus}
          onBackfill={() =>
            dataminingApi.triggerBackfill()
              .then(() => dataminingApi.embedStatus().then(setEmbedStatus).catch(() => {}))
              .catch(() => {})
          }
          onReset={() =>
            dataminingApi.resetEmbeddings()
              .then(() => dataminingApi.embedStatus().then(setEmbedStatus).catch(() => {}))
              .catch(() => {})
          }
        />
      )}

      <div className="flex items-center gap-2">
        <button
          onClick={startExport}
          disabled={exportState === "running"}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-white/[4%] hover:bg-white/[8%] text-zinc-400 hover:text-zinc-200 disabled:opacity-40 transition-colors"
        >
          <Download size={12} />
          {exportState === "running" ? "exportiert…" : "DB Export"}
        </button>
        {exportState === "done" && exportFile && (
          <button
            onClick={() => dataminingApi.downloadExport(exportFile).catch(() => {})}
            className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors"
          >
            ↓ {exportFile} ({exportSizeMb} MB)
          </button>
        )}
        <button
          onClick={() => importRef.current?.click()}
          disabled={importState === "running"}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-white/[4%] hover:bg-white/[8%] text-zinc-400 hover:text-zinc-200 disabled:opacity-40 transition-colors"
        >
          <Upload size={12} />
          {importState === "running" ? "importiert…" : importState === "done" ? "importiert ✓" : "DB Import"}
        </button>
        <input ref={importRef} type="file" accept=".dump,.dump.gz" className="hidden" onChange={handleImport} />
        <button
          onClick={startSqliteImport}
          disabled={sqliteImport?.running ?? false}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-white/[4%] hover:bg-white/[8%] text-zinc-400 hover:text-zinc-200 disabled:opacity-40 transition-colors"
        >
          <Upload size={12} />
          {sqliteImport?.running
            ? `SQLite… ${sqliteImport.sessions}/${sqliteImport.total}`
            : sqliteImport && !sqliteImport.running && sqliteImport.sessions > 0
            ? "SQLite ✓"
            : "SQLite Import"}
        </button>
      </div>

      {tab === "feed" && <LiveFeedTab active={tab === "feed"} />}
      {tab === "search" && <SearchTab />}
      {tab === "sessions" && <SessionsTab active={tab === "sessions"} />}
      {tab === "graph" && <GraphTab />}
    </div>
  )
}

function EmbedStatusBar({ status, onBackfill, onReset }: {
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
