import { useCallback, useEffect, useState } from "react"
import { AlertTriangle, CheckCircle2, Loader2, ShieldCheck, XCircle } from "lucide-react"
import { CockpitShell } from "@/features/cockpit/CockpitShell"
import { CockpitTopbar } from "@/features/cockpit/CockpitTopbar"
import { aiSecurityApi, type AISecurityHealth, type AISecurityScan } from "./api"

const text: Record<string, Record<string, string>> = {
  de: {
    title: "AI-Sicherheit",
    intro: "Lokale AI-Dienste auf bekannte Infrastruktur-Schwachstellen prüfen.",
    unavailable: "Der Scanner ist nicht erreichbar.",
    notConfigured: "Kein AI-Infra-Guard ist konfiguriert.",
    target: "Freigegebenes Ziel",
    scan: "Scan starten",
    scanning: "Scan läuft…",
    noTargets: "Es sind keine Scan-Ziele freigegeben.",
    recent: "Letzte Scans",
    empty: "Noch keine Scans.",
    completed: "abgeschlossen",
    failed: "fehlgeschlagen",
    queued: "wartend",
    running: "läuft",
    report: "Report",
    noReport: "Noch kein Report verfügbar.",
    error: "Fehler",
  },
  en: {
    title: "AI Security",
    intro: "Check local AI services for known infrastructure vulnerabilities.",
    unavailable: "The scanner is not reachable.",
    notConfigured: "No AI-Infra-Guard is configured.",
    target: "Allowed target",
    scan: "Start scan",
    scanning: "Scan running…",
    noTargets: "No scan targets are allowed.",
    recent: "Recent scans",
    empty: "No scans yet.",
    completed: "completed",
    failed: "failed",
    queued: "queued",
    running: "running",
    report: "Report",
    noReport: "No report available yet.",
    error: "Error",
  },
}

function language(): "de" | "en" {
  return document.documentElement.lang.toLowerCase().startsWith("de") ? "de" : "en"
}

function StatusIcon({ status }: { status: AISecurityScan["status"] }) {
  if (status === "completed") return <CheckCircle2 size={16} className="text-emerald-500" />
  if (status === "failed") return <XCircle size={16} className="text-red-500" />
  return <Loader2 size={16} className="animate-spin text-amber-500" />
}

export function AISecurityPage() {
  const labels = text[language()]
  const [health, setHealth] = useState<AISecurityHealth | null>(null)
  const [targets, setTargets] = useState<string[]>([])
  const [scans, setScans] = useState<AISecurityScan[]>([])
  const [selectedTarget, setSelectedTarget] = useState("")
  const [selectedScan, setSelectedScan] = useState<AISecurityScan | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const [nextHealth, nextTargets, nextScans] = await Promise.all([
        aiSecurityApi.health(),
        aiSecurityApi.targets(),
        aiSecurityApi.scans(),
      ])
      setHealth(nextHealth)
      setTargets(nextTargets)
      setScans(nextScans)
      setSelectedTarget((current) => current || nextTargets[0] || "")
      setSelectedScan((current) =>
        current ? nextScans.find((scan) => scan.id === current.id) ?? current : nextScans[0] ?? null,
      )
      setError(null)
    } catch {
      setError(labels.unavailable)
    }
  }, [labels.unavailable])

  useEffect(() => {
    void refresh()
  }, [refresh])

  useEffect(() => {
    if (!scans.some((scan) => scan.status === "queued" || scan.status === "running")) return
    const timer = window.setInterval(() => void refresh(), 5000)
    return () => window.clearInterval(timer)
  }, [refresh, scans])

  async function startScan() {
    if (!selectedTarget) return
    setBusy(true)
    setError(null)
    try {
      const scan = await aiSecurityApi.createScan(selectedTarget)
      setSelectedScan(scan)
      await refresh()
    } catch {
      setError(labels.error)
    } finally {
      setBusy(false)
    }
  }

  const statusLabel = (status: AISecurityScan["status"]) => labels[status]

  return (
    <CockpitShell title={labels.title} className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]" hideHeader>
      <CockpitTopbar active="/ai-security" context={labels.intro} />
      <main className="min-h-0 flex-1 overflow-y-auto p-4">
        <div className="mx-auto max-w-5xl space-y-6">
      <header className="flex items-start gap-4">
        <div className="rounded-xl bg-indigo-500/10 p-3 text-indigo-500"><ShieldCheck size={28} /></div>
        <div>
          <h1 className="text-2xl font-semibold">{labels.title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{labels.intro}</p>
        </div>
      </header>

      {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"><AlertTriangle className="mr-2 inline" size={16} />{error}</div>}
      {health && !health.configured && <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">{labels.notConfigured}</div>}
      {health && health.configured && !health.reachable && <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">{labels.unavailable}</div>}

      <section className="rounded-xl border bg-card p-5 shadow-sm">
        <div className="flex flex-wrap items-end gap-3">
          <label className="min-w-72 flex-1 text-sm font-medium">
            {labels.target}
            <select
              className="mt-2 block w-full rounded-md border bg-background px-3 py-2 text-sm"
              value={selectedTarget}
              onChange={(event) => setSelectedTarget(event.target.value)}
              disabled={targets.length === 0 || busy}
            >
              {targets.length === 0 && <option value="">{labels.noTargets}</option>}
              {targets.map((target) => <option key={target} value={target}>{target}</option>)}
            </select>
          </label>
          <button
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50"
            onClick={() => void startScan()}
            disabled={!selectedTarget || busy || health?.reachable !== true}
          >
            {busy ? labels.scanning : labels.scan}
          </button>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
        <div className="rounded-xl border bg-card p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold">{labels.recent}</h2>
          {scans.length === 0 ? <p className="text-sm text-muted-foreground">{labels.empty}</p> : (
            <div className="space-y-2">
              {scans.map((scan) => (
                <button key={scan.id} className={`flex w-full items-center gap-3 rounded-lg border p-3 text-left text-sm ${selectedScan?.id === scan.id ? "border-primary bg-primary/5" : ""}`} onClick={() => setSelectedScan(scan)}>
                  <StatusIcon status={scan.status} />
                  <span className="min-w-0 flex-1 truncate">{scan.target_url}</span>
                  <span className="text-xs text-muted-foreground">{statusLabel(scan.status)}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="rounded-xl border bg-card p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold">{labels.report}</h2>
          {selectedScan?.result ? <pre className="max-h-[32rem] overflow-auto rounded-lg bg-muted p-4 text-xs">{JSON.stringify(selectedScan.result, null, 2)}</pre> : <p className="text-sm text-muted-foreground">{selectedScan?.error_code ?? labels.noReport}</p>}
        </div>
      </section>
        </div>
      </main>
    </CockpitShell>
  )
}
