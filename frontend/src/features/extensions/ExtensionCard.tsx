import {
  Brain, Code2, ExternalLink, FileText, GitBranch, Gamepad2, Lock,
  Network, Search, ShieldOff, Package, Container,
} from "lucide-react"
import { useState } from "react"
import type { Extension, InstallMode } from "./types"

const ICON_MAP: Record<string, React.ElementType> = {
  GitBranch, Brain, Code2, FileText, Search, Network, Lock, ShieldOff, Gamepad2,
}

function ExtIcon({ name }: { name: string }) {
  const Icon = ICON_MAP[name] ?? Package
  return <Icon size={20} />
}

function StatusBadge({ ext }: { ext: Extension }) {
  if (!ext.installed) return (
    <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-zinc-800 text-zinc-400 border border-white/[6%]">
      Nicht installiert
    </span>
  )
  if (ext.active && ext.healthy) return (
    <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
      Aktiv
    </span>
  )
  if (ext.active) return (
    <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/15 text-amber-400 border border-amber-500/30">
      Läuft (nicht erreichbar)
    </span>
  )
  return (
    <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-rose-500/15 text-rose-400 border border-rose-500/30">
      Gestoppt
    </span>
  )
}

interface Props {
  ext: Extension
  onInstall: (mode: InstallMode) => void
  onUninstall: (mode: InstallMode) => void
}

export function ExtensionCard({ ext, onInstall, onUninstall }: Props) {
  const hasDocker = !!ext.docker && ext.docker_available
  const [mode, setMode] = useState<InstallMode>("native")

  const openUrl = (() => {
    if (ext.install_mode === "docker" && ext.docker?.open_url)
      return `http://${window.location.hostname}${ext.docker.open_url}`
    if (ext.open_url)
      return `http://${window.location.hostname}${ext.open_url}`
    return null
  })()

  return (
    <div className="flex flex-col gap-3 p-4 rounded-xl bg-white/[2%] border border-white/[6%] hover:border-white/[10%] transition-colors">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-violet-500/10 text-violet-400 shrink-0">
          <ExtIcon name={ext.icon} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-zinc-100 text-sm">{ext.name}</span>
            <StatusBadge ext={ext} />
            {ext.install_mode === "docker" && (
              <span className="flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] bg-blue-500/10 border border-blue-500/20 text-blue-400">
                <Container size={9} /> Docker
              </span>
            )}
          </div>
          <p className="text-xs text-zinc-500 mt-0.5 line-clamp-2">{ext.description}</p>
        </div>
      </div>

      {/* Mode-Toggle — nur sichtbar wenn Docker verfügbar + Extension hat docker-Block + noch nicht installiert */}
      {hasDocker && !ext.installed && (
        <div className="flex rounded-lg overflow-hidden border border-white/[8%] text-xs">
          {(["native", "docker"] as InstallMode[]).map((m) => (
            <button key={m} onClick={() => setMode(m)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 transition-colors ${
                mode === m
                  ? "bg-violet-600 text-white"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[5%]"
              }`}>
              {m === "docker" ? <><Container size={11} /> Docker</> : <><Package size={11} /> Nativ</>}
            </button>
          ))}
        </div>
      )}

      <div className="flex items-center gap-2">
        {!ext.installed ? (
          <button onClick={() => onInstall(mode)}
            className="flex-1 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-medium transition-colors">
            Installieren
          </button>
        ) : (
          <>
            {openUrl && (
              <a href={openUrl} target="_blank" rel="noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[5%] border border-white/[8%] text-zinc-300 text-xs hover:bg-white/[8%] transition-colors">
                <ExternalLink size={11} /> Öffnen
              </a>
            )}
            <button onClick={() => onUninstall(ext.install_mode ?? "native")}
              className="flex-1 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 text-rose-400 text-xs font-medium transition-colors">
              Deinstallieren
            </button>
          </>
        )}
      </div>
    </div>
  )
}
