import { useEffect, useState } from "react"
import { Activity, Bot, Users } from "lucide-react"
import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { cn } from "@/shared/cn"

interface Agent { id: string; type: string; name: string; owner: string | null }
interface User { username: string; role: string }

function StatCard({ icon: Icon, label, value, from, to, glow }: {
  icon: typeof Bot; label: string; value: string | number
  from: string; to: string; glow: string
}) {
  return (
    <div className={cn(
      "group relative rounded-xl border border-white/[8%] bg-white/[3%] p-5 flex items-center gap-4",
      "hover:border-white/20 hover:bg-white/[6%] hover:-translate-y-1 transition-all duration-200",
      `hover:shadow-2xl ${glow}`
    )}>
      <div className={cn("relative w-11 h-11 rounded-full flex items-center justify-center bg-gradient-to-br shrink-0", from, to)}>
        <Icon size={20} className="text-white" />
        <div className={cn("absolute inset-0 rounded-full bg-gradient-to-br blur-md opacity-50 -z-10 scale-125", from, to)} />
      </div>
      <div>
        <p className="text-zinc-500 text-xs uppercase tracking-wide">{label}</p>
        <p className="text-2xl font-bold text-white mt-0.5">{value}</p>
      </div>
    </div>
  )
}

function AgentRow({ agent }: { agent: Agent }) {
  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-white/[5%] last:border-0">
      <div className="relative shrink-0">
        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500/30 to-violet-600/30 flex items-center justify-center">
          <Bot size={13} className="text-violet-400" />
        </div>
        <div className="absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-400 border border-zinc-900 shadow-[0_0_5px_rgba(52,211,153,0.55)]" />
      </div>
      <span className="text-sm text-zinc-200 flex-1 truncate">{agent.name}</span>
      <span className="text-xs text-zinc-600 shrink-0">{agent.owner}</span>
    </div>
  )
}

export function DashboardPage() {
  const { role } = useAuthStore()
  const [health, setHealth] = useState<string>("…")
  const [agents, setAgents] = useState<Agent[]>([])
  const [users, setUsers] = useState<User[]>([])

  useEffect(() => {
    api.get<{ status: string; version: string }>("/health")
      .then((r) => setHealth(`${r.status} · v${r.version}`))
      .catch(() => setHealth("Fehler"))
    api.get<Agent[]>("/agents").then(setAgents).catch(() => {})
    if (role === "admin") api.get<User[]>("/users").then(setUsers).catch(() => {})
  }, [role])

  const masters = agents.filter((a) => a.type === "master")
  const specialists = agents.filter((a) => a.type === "specialist")

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-xl font-bold text-white">Dashboard</h1>
        <p className="text-zinc-500 text-sm mt-0.5">Systemübersicht</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        <StatCard icon={Activity} label="Status" value={health}
          from="from-emerald-500" to="to-teal-600"
          glow="hover:shadow-emerald-500/15" />
        <StatCard icon={Bot} label="Agenten" value={agents.length}
          from="from-indigo-600" to="to-violet-700"
          glow="hover:shadow-violet-500/18" />
        {role === "admin" && (
          <StatCard icon={Users} label="Benutzer" value={users.length}
            from="from-blue-500" to="to-indigo-600"
            glow="hover:shadow-indigo-500/18" />
        )}
      </div>

      {masters.length > 0 && (
        <div className="rounded-xl border border-white/[8%] bg-white/[3%] p-5 hover:border-white/[12%] transition-colors">
          <h3 className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500 mb-3">
            Masteragenten
          </h3>
          {masters.map((a) => <AgentRow key={a.id} agent={a} />)}
          {specialists.length > 0 && (
            <p className="text-xs text-zinc-600 pt-2.5">
              + {specialists.length} Spezialist{specialists.length !== 1 ? "en" : ""} verfügbar
            </p>
          )}
        </div>
      )}
    </div>
  )
}
