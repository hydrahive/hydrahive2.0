import { useEffect, useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { ArrowLeft, FileText, Gauge, Settings, Terminal as TerminalIcon } from "lucide-react"
import type { Container } from "./types"
import { containersApi } from "./api"
import { ContainerStatusBadge } from "./StatusBadge"
import { ConsolePane } from "./ConsolePane"
import { ContainerLogPane } from "./ContainerLogPane"
import { ContainerStatsPane } from "./ContainerStatsPane"
import { ContainerConfigPane } from "./ContainerConfigPane"

type Tab = "console" | "logs" | "stats" | "config"

export function ContainerDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [container, setContainer] = useState<Container | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>("console")

  useEffect(() => {
    if (!id) return
    let alive = true
    async function load() {
      try {
        const c = await containersApi.get(id!)
        if (alive) { setContainer(c); setError(null) }
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : String(e))
      }
    }
    void load()
    const t = setInterval(load, 5000)
    return () => { alive = false; clearInterval(t) }
  }, [id])

  if (error) {
    return (
      <div className="space-y-3">
        <BackLink />
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div>
      </div>
    )
  }

  if (!container) {
    return (
      <div className="space-y-3">
        <BackLink />
        <p className="text-sm text-zinc-500">Lade…</p>
      </div>
    )
  }

  const running = container.actual_state === "running"

  return (
    <div className="space-y-4 max-w-7xl flex flex-col" style={{ height: "calc(100vh - 8rem)" }}>
      <div className="flex items-center gap-3 flex-shrink-0">
        <button onClick={() => navigate("/containers")}
          className="p-2 rounded-lg bg-white/[5%] border border-white/[8%] text-zinc-400 hover:text-zinc-200">
          <ArrowLeft size={14} />
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-bold text-white truncate">{container.name}</h1>
            <ContainerStatusBadge state={container.actual_state} />
          </div>
          <p className="text-xs text-zinc-500 font-mono truncate">{container.image}</p>
        </div>
      </div>

      <div className="flex items-center gap-1 border-b border-white/[8%] flex-shrink-0">
        <TabBtn active={tab === "console"} onClick={() => setTab("console")} disabled={!running}>
          <TerminalIcon size={12} /> Console
        </TabBtn>
        <TabBtn active={tab === "logs"} onClick={() => setTab("logs")}>
          <FileText size={12} /> Logs
        </TabBtn>
        <TabBtn active={tab === "stats"} onClick={() => setTab("stats")}>
          <Gauge size={12} /> Stats
        </TabBtn>
        <TabBtn active={tab === "config"} onClick={() => setTab("config")}>
          <Settings size={12} /> Konfig
        </TabBtn>
      </div>

      <div className="flex-1 min-h-0 rounded-xl border border-white/[8%] bg-zinc-950 overflow-hidden">
        {tab === "console" && running && <ConsolePane containerId={container.container_id} className="h-full" />}
        {tab === "console" && !running && (
          <div className="h-full flex items-center justify-center text-sm text-zinc-500">
            Container läuft nicht — Konsole nicht verfügbar.
          </div>
        )}
        {tab === "logs" && <ContainerLogPane containerId={container.container_id} />}
        {tab === "stats" && <ContainerStatsPane container={container} />}
        {tab === "config" && <ContainerConfigPane containerId={container.container_id} />}
      </div>
    </div>
  )
}

function BackLink() {
  return (
    <Link to="/containers" className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200">
      <ArrowLeft size={12} /> Zurück zu Container
    </Link>
  )
}

function TabBtn({ active, onClick, disabled, children }: {
  active: boolean
  onClick: () => void
  disabled?: boolean
  children: React.ReactNode
}) {
  return (
    <button onClick={onClick} disabled={disabled}
      className={`flex items-center gap-1.5 px-3 py-2 text-xs border-b-2 transition-colors disabled:opacity-30 disabled:cursor-not-allowed ${
        active ? "border-violet-500 text-violet-200" : "border-transparent text-zinc-400 hover:text-zinc-200"
      }`}>
      {children}
    </button>
  )
}
