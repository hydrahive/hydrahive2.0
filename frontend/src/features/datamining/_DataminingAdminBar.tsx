import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Download, Upload } from "lucide-react"
import { dataminingApi } from "./api"
import { IssueImportButtons, IssueImportForm } from "./_IssueImportForm"
import { SourceImportButtons } from "./_SourceImportButtons"

type RunState = "idle" | "running" | "done" | "error"

const actionBtn = "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-white/[4%] hover:bg-white/[8%] text-zinc-400 hover:text-zinc-200 disabled:opacity-40 transition-colors"

/** Export/Import/Merge/Quellen — nur für Admins (Backend verlangt require_admin). */
export function DataminingAdminBar() {
  const { t } = useTranslation("datamining")
  const [exportState, setExportState] = useState<RunState>("idle")
  const [exportFile, setExportFile] = useState<string | null>(null)
  const [exportSizeMb, setExportSizeMb] = useState<number>(0)
  const [importState, setImportState] = useState<RunState>("idle")
  const importRef = useRef<HTMLInputElement>(null)
  const [mergeState, setMergeState] = useState<RunState>("idle")
  const [mergeError, setMergeError] = useState<string | null>(null)
  const mergeRef = useRef<HTMLInputElement>(null)
  const [sqlite, setSqlite] = useState<{ running: boolean; sessions: number; total: number } | null>(null)
  const [shellState, setShellState] = useState<RunState>("idle")
  const [shellInserted, setShellInserted] = useState(0)
  const shellRef = useRef<HTMLInputElement>(null)
  const [issueForm, setIssueForm] = useState<"github" | "gitea" | null>(null)

  useEffect(() => {
    dataminingApi.exportStatus().then((s) => {
      if (s.done && s.filename) { setExportState("done"); setExportFile(s.filename); setExportSizeMb(s.size_mb) }
    }).catch(() => {})
    dataminingApi.importStatus().then((s) => { if (s.running) setImportState("running") }).catch(() => {})
    dataminingApi.mergeImportStatus().then((s) => { if (s.running) setMergeState("running") }).catch(() => {})
    dataminingApi.sqliteImportStatus().then((s) => {
      if (s.running) setSqlite({ running: true, sessions: s.sessions, total: s.total_sessions })
    }).catch(() => {})
  }, [])

  function poll<T>(read: () => Promise<T>, onTick: (s: T) => boolean) {
    const iv = setInterval(async () => {
      const s = await read().catch(() => null)
      if (s && onTick(s)) clearInterval(iv)
    }, 2000)
  }

  async function startExport() {
    setExportState("running"); setExportFile(null)
    await dataminingApi.startExport().catch(() => {})
    poll(dataminingApi.exportStatus, (s) => {
      if (s.done) { setExportState("done"); setExportFile(s.filename); setExportSizeMb(s.size_mb); return true }
      if (s.error) { setExportState("error"); return true }
      return false
    })
  }

  async function handleImport(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]; if (!file) return
    setImportState("running")
    const ok = await dataminingApi.startImport(file).then(() => true).catch(() => false)
    if (!ok) { setImportState("error"); return }
    poll(dataminingApi.importStatus, (s) => {
      if (s.done) { setImportState("done"); return true }
      if (s.error) { setImportState("error"); return true }
      return false
    })
  }

  async function handleMerge(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]; if (!file) return
    setMergeState("running"); setMergeError(null)
    const started = await dataminingApi.startMergeImport(file).catch((err: Error) => {
      setMergeState("error"); setMergeError(err.message); return null
    })
    if (!started) return
    poll(dataminingApi.mergeImportStatus, (s) => {
      if (s.done) { setMergeState("done"); return true }
      if (s.error) { setMergeState("error"); setMergeError(s.error); return true }
      return false
    })
  }

  async function handleShell(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]; if (!file) return
    e.target.value = ""
    const username = window.prompt(t("shell.prompt"))?.trim()
    if (!username) return
    setShellState("running")
    try {
      const result = await dataminingApi.startShellImport(file, username)
      setShellInserted(result.inserted ?? 0)
      setShellState("done")
    } catch {
      setShellState("error")
    }
  }

  async function startSqlite() {
    await dataminingApi.startSqliteImport().catch(() => {})
    setSqlite({ running: true, sessions: 0, total: 0 })
    poll(dataminingApi.sqliteImportStatus, (s) => {
      setSqlite({ running: s.running, sessions: s.sessions, total: s.total_sessions })
      return !s.running
    })
  }

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <button onClick={startExport} disabled={exportState === "running"} className={actionBtn}>
          <Download size={12} />
          {exportState === "running" ? "exportiert…" : "DB Export"}
        </button>
        {exportState === "done" && exportFile && (
          <button onClick={() => dataminingApi.downloadExport(exportFile).catch(() => {})}
            className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors">
            ↓ {exportFile} ({exportSizeMb} MB)
          </button>
        )}
        <button onClick={() => importRef.current?.click()} disabled={importState === "running"} className={actionBtn}>
          <Upload size={12} />
          {importState === "running" ? "importiert…" : importState === "done" ? "importiert ✓" : "DB Import"}
        </button>
        <input ref={importRef} type="file" accept=".dump,.dump.gz" className="hidden" onChange={handleImport} />
        <button onClick={() => mergeRef.current?.click()} disabled={mergeState === "running"} className={actionBtn}
          title={mergeState === "error" && mergeError ? mergeError : undefined}>
          <Upload size={12} />
          {mergeState === "running" ? "merge…" : mergeState === "done" ? "merge ✓" : mergeState === "error" ? "merge ✗" : "DB Merge"}
        </button>
        <input ref={mergeRef} type="file" accept=".dump,.dump.gz" className="hidden" onChange={handleMerge} />
        <button onClick={startSqlite} disabled={sqlite?.running ?? false} className={actionBtn}>
          <Upload size={12} />
          {sqlite?.running ? `SQLite… ${sqlite.sessions}/${sqlite.total}`
            : sqlite && sqlite.sessions > 0 ? "SQLite ✓" : "SQLite Import"}
        </button>
        <button onClick={() => shellRef.current?.click()} disabled={shellState === "running"} className={actionBtn}
          title="~/.bash_history oder ~/.zsh_history importieren">
          <Upload size={12} />
          {shellState === "running" ? t("shell.running")
            : shellState === "done" ? `Shell ✓ (${shellInserted})`
            : shellState === "error" ? t("shell.error")
            : t("shell.button")}
        </button>
        <input ref={shellRef} type="file" className="hidden" onChange={handleShell} />
        <IssueImportButtons active={issueForm} onToggle={(v) => setIssueForm((f) => f === v ? null : v)} />
        <SourceImportButtons />
      </div>
      {issueForm && <IssueImportForm variant={issueForm} />}
    </>
  )
}
