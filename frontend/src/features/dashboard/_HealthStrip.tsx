import { Link } from "react-router-dom"
import { CheckCircle2, Link2, Network, Radio, Server, XCircle } from "lucide-react"
import type { DashboardHealth } from "./api"

interface Props {
  health: DashboardHealth
}

interface Pill {
  label: string
  icon: typeof Server
  state: "ok" | "warn" | "off"
  href: string
}

export function HealthStrip({ health }: Props) {
  const pills: Pill[] = [
    {
      label: "Backend",
      icon: Server,
      state: health.backend.ok ? "ok" : "warn",
      href: "/system",
    },
    {
      label: "AgentLink",
      icon: Link2,
      state: !health.agentlink.configured ? "off"
        : health.agentlink.ok ? "ok" : "warn",
      href: "/system",
    },
    {
      label: "Bridge",
      icon: Network,
      state: health.bridge.ok ? "ok" : "warn",
      href: "/system",
    },
    {
      label: "Tailscale",
      icon: Radio,
      state: !health.tailscale.configured ? "off"
        : health.tailscale.ok ? "ok" : "warn",
      href: "/system",
    },
  ]
  return (
    <div className="flex flex-wrap gap-2">
      {pills.map((p) => {
        const tone = p.state === "ok" ? "emerald"
          : p.state === "warn" ? "amber" : "zinc"
        const cls: Record<string, string> = {
          emerald: "bg-emerald-500/[8%] border-emerald-500/20 text-emerald-300 hover:bg-emerald-500/15",
          amber: "bg-amber-500/[8%] border-amber-500/20 text-amber-300 hover:bg-amber-500/15",
          zinc: "bg-zinc-500/[6%] border-zinc-500/15 text-zinc-500 hover:bg-zinc-500/10",
        }
        const StatusIcon = p.state === "ok" ? CheckCircle2
          : p.state === "warn" ? XCircle : null
        return (
          <Link key={p.label} to={p.href}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] transition-colors ${cls[tone]}`}>
            <p.icon size={11} />
            <span className="font-medium">{p.label}</span>
            {StatusIcon && <StatusIcon size={11} />}
          </Link>
        )
      })}
    </div>
  )
}
