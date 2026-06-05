import { type CSSProperties, useEffect, useState } from "react"
import {
  Brain, Code2, ExternalLink, FileText, GitBranch, Gamepad2,
  Lock, Network, Search, ShieldOff, Package, Loader2,
} from "lucide-react"
import { useTranslation } from "react-i18next"
import { rgbFor } from "@/shared/colors"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { fetchExtensions } from "@/features/extensions/api"
import type { Extension } from "@/features/extensions/types"

const ICON_MAP: Record<string, React.ElementType> = {
  GitBranch, Brain, Code2, FileText, Search, Network, Lock, ShieldOff, Gamepad2,
}

function ExtIcon({ name }: { name: string }) {
  const Icon = ICON_MAP[name] ?? Package
  return <Icon size={18} />
}

function ExtTile({ ext }: { ext: Extension }) {
  const openUrl = (() => {
    const raw = (ext.install_mode === "docker" && ext.docker?.open_url)
      ? ext.docker.open_url
      : (ext.open_url ?? "")
    if (!raw) return null
    if (raw.startsWith("http")) return raw
    return `http://${window.location.hostname}${raw}`
  })()

  const statusColor = ext.active && ext.healthy
    ? "bg-emerald-400 shadow-[0_0_4px_rgba(52,211,153,0.6)]"
    : ext.active
    ? "bg-amber-400"
    : "bg-zinc-600"

  const tile = (
    <div className="tile relative flex flex-col items-center gap-1.5 p-2.5 transition-all group cursor-pointer" style={{ "--c": rgbFor("/mcp") } as CSSProperties}>
      <div className={`absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full ${statusColor}`} />
      <div className="w-9 h-9 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
        <ExtIcon name={ext.icon} />
      </div>
      <span className="text-[10px] text-zinc-400 text-center leading-tight w-full truncate">{ext.name}</span>
      {openUrl && (
        <ExternalLink
          size={9}
          className="absolute bottom-1.5 right-1.5 text-zinc-600 opacity-0 group-hover:opacity-100 transition-opacity"
        />
      )}
    </div>
  )

  return openUrl ? (
    <a href={openUrl} target="_blank" rel="noreferrer">{tile}</a>
  ) : (
    <>{tile}</>
  )
}

export function BuddyExtensionsPanel() {
  const { t } = useTranslation("buddy")
  const [extensions, setExtensions] = useState<Extension[] | null>(null)

  useEffect(() => {
    fetchExtensions()
      .then((all) => setExtensions(all.filter((e) => e.installed)))
      .catch(() => setExtensions([]))
  }, [])

  return (
    <CollapsibleBox
      boxId="buddy-extensions"
      icon={<span className="text-sm">🧩</span>}
      title={t("boxes.extensions")}
      color={rgbFor("/mcp")}
      defaultCollapsed
      className="w-60"
    >
      <div className="p-3">
        {extensions === null ? (
          <div className="flex justify-center py-4">
            <Loader2 size={14} className="text-zinc-600 animate-spin" />
          </div>
        ) : extensions.length === 0 ? (
          <p className="text-xs text-zinc-600 text-center py-3 italic">Keine Extensions installiert</p>
        ) : (
          <div className="grid grid-cols-3 gap-2">
            {extensions.map((ext) => (
              <ExtTile key={ext.id} ext={ext} />
            ))}
          </div>
        )}
      </div>
    </CollapsibleBox>
  )
}
