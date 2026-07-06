import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Download, Pickaxe, Upload } from "lucide-react"
import { LiveFeedTab } from "./LiveFeedTab"
import { SearchTab } from "./SearchTab"
import { SessionsTab } from "./SessionsTab"
import { GraphTab } from "./GraphTab"
import { StatsTab } from "./StatsTab"
import { dataminingApi } from "./api"
import { EmbedStatusBar, type EmbedStatus } from "./_EmbedStatusBar"
import { IssueImportButtons, IssueImportForm } from "./_IssueImportForm"
import { SourceImportButtons } from "./_SourceImportButtons"
import { HelpButton } from "@/i18n/HelpButton"

const TABS = ["feed", "search", "sessions", "stats", "graph"] as const
type Tab = typeof TABS[number]

export function DataminingPage() {
  const { t } = useTranslation("datamining")
  const [tab, setTab] = useState<Tab>("feed")
  const [embedStatus, setEmbedStatus] = useState<EmbedStatus | null>(null)
  const [exportState, setExportState] = useState<"idle" | "running" | "done" | "error">("idle")
  const [exportFile, setExportFile] = useState<string | null>(null)
  const [exportSizeMb, setExportSizeMb] = useState<number>(0)
  const [importState, setImportState] = useState<"idle" | "running" | "done" | "error">("idle")
  const importRef = useRef<HTMLInputElement>(null)
  const [mergeImportState, setMergeImportState] = useState<"idle" | "running" | "done" | "error">("idle")
  const [mergeImportError, setMergeImportError] = useState<string | null>(null)
  const mergeImportRef = useRef<HTMLInputElement>(null)
  const [sqliteImport, setSqliteImport] = useState<{ running: boolean; sessions: number; total: number } | null>(null)
  const [shellImport, setShellImport] = useState<"idle" | "running" | "done" | "error">("idle")
  const [shellInserted, setShellInserted] = useState(0)
  const shellImportRef = useRef<HTMLInputElement>(null)
  const [issueForm, setIssueForm] = useState<"github" | "gitea" | null>(null)

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
    dataminingApi.mergeImportStatus().then((s) => {
      if (s.running) setMergeImportState("running")
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

  async function handleMergeImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]; if (!file) return
    setMergeImportState("running"); setMergeImportError(null)
    const started = await dataminingApi.startMergeImport(file).catch((err: Error) => {
      setMergeImportState("error"); setMergeImportError(err.message); return null
    })
    if (!started) return
    const poll = setInterval(async () => {
      const s = await dataminingApi.mergeImportStatus().catch(() => null)
      if (!s) return
      if (s.done) { setMergeImportState("done"); clearInterval(poll) }
      else if (s.error) { setMergeImportState("error"); setMergeImportError(s.error); clearInterval(poll) }
    }, 2000)
  }

  async function handleShellImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]; if (!file) return
    e.target.value = ""
    setShellImport("running")
    try {
      const username = window.prompt(t("shell.prompt"), "till") ?? "till"
      const result = await dataminingApi.startShellImport(file, username)
      setShellInserted(result.inserted ?? 0)
      setShellImport("done")
    } catch {
      setShellImport("error")
    }
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

  const actionBtn = "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-white/[4%] hover:bg-white/[8%] text-zinc-400 hover:text-zinc-200 disabled:opacity-40 transition-colors"

  return (
    <div className="space-y-4 max-w-4xl">
      <div className="flex items-center gap-3">
        <Pickaxe className="text-amber-400" size={20} />
        <div>
          <h1 className="text-xl font-semibold text-zinc-100">{t("title")}</h1>
          <p className="text-xs text-zinc-500 mt-0.5">{t("subtitle")}</p>
        </div>
        <HelpButton topic="datamining" />
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

      {embedStatus?.active && embedStatus && (
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
          onRechunk={() =>
            dataminingApi.triggerRechunk()
              .then(() => dataminingApi.embedStatus().then(setEmbedStatus).catch(() => {}))
              .catch(() => {})
          }
        />
      )}

      <div className="flex items-center gap-2">
        <button onClick={startExport} disabled={exportState === "running"} className={actionBtn}>
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
        <button onClick={() => importRef.current?.click()} disabled={importState === "running"} className={actionBtn}>
          <Upload size={12} />
          {importState === "running" ? "importiert…" : importState === "done" ? "importiert ✓" : "DB Import"}
        </button>
        <input ref={importRef} type="file" accept=".dump,.dump.gz" className="hidden" onChange={handleImport} />
        <button
          onClick={() => mergeImportRef.current?.click()}
          disabled={mergeImportState === "running"}
          className={actionBtn}
          title={mergeImportState === "error" && mergeImportError ? mergeImportError : undefined}
        >
          <Upload size={12} />
          {mergeImportState === "running" ? "merge…" : mergeImportState === "done" ? "merge ✓" : mergeImportState === "error" ? "merge ✗" : "DB Merge"}
        </button>
        <input ref={mergeImportRef} type="file" accept=".dump,.dump.gz" className="hidden" onChange={handleMergeImport} />
        <button onClick={startSqliteImport} disabled={sqliteImport?.running ?? false} className={actionBtn}>
          <Upload size={12} />
          {sqliteImport?.running
            ? `SQLite… ${sqliteImport.sessions}/${sqliteImport.total}`
            : sqliteImport && !sqliteImport.running && sqliteImport.sessions > 0
            ? "SQLite ✓"
            : "SQLite Import"}
        </button>
        <button
          onClick={() => shellImportRef.current?.click()}
          disabled={shellImport === "running"}
          className={actionBtn}
          title="~/.bash_history oder ~/.zsh_history importieren"
        >
          <Upload size={12} />
          {shellImport === "running" ? t("shell.running")
            : shellImport === "done" ? `Shell ✓ (${shellInserted})`
            : shellImport === "error" ? t("shell.error")
            : t("shell.button")}
        </button>
        <input ref={shellImportRef} type="file" className="hidden" onChange={handleShellImport} />
        <IssueImportButtons
          active={issueForm}
          onToggle={(v) => setIssueForm(f => f === v ? null : v)}
        />
        <SourceImportButtons />
      </div>

      {issueForm && <IssueImportForm variant={issueForm} />}

      {tab === "feed" && <LiveFeedTab active={tab === "feed"} />}
      {tab === "search" && <SearchTab />}
      {tab === "sessions" && <SessionsTab active={tab === "sessions"} />}
      {tab === "stats" && <StatsTab active={tab === "stats"} />}
      {tab === "graph" && <GraphTab />}
    </div>
  )
}
