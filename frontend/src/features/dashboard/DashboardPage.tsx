import { useEffect, useState } from "react"
import { Bot, Users, Activity } from "lucide-react"
import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"

interface Agent { id: string; type: string; name: string; owner: string | null }
interface User { username: string; role: string }

function StatCard({ icon: Icon, label, value, gradient }: {
  icon: typeof Bot; label: string; value: string | number; gradient: string
}) {
  return (
    <div className="bg-card border border-border rounded-xl p-5 flex items-center gap-4">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${gradient}`}>
        <Icon size={20} className="text-white" />
      </div>
      <div>
        <p className="text-muted-foreground text-sm">{label}</p>
        <p className="text-2xl font-semibold text-foreground">{value}</p>
      </div>
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
      .then((r) => setHealth(`${r.status} v${r.version}`))
      .catch(() => setHealth("Fehler"))

    api.get<Agent[]>("/agents").then(setAgents).catch(() => {})

    if (role === "admin") {
      api.get<User[]>("/users").then(setUsers).catch(() => {})
    }
  }, [role])

  const masterAgents = agents.filter((a) => a.type === "master")
  const specialists = agents.filter((a) => a.type === "specialist")

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-foreground">Dashboard</h2>
        <p className="text-muted-foreground text-sm mt-1">Systemübersicht</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard
          icon={Activity}
          label="Status"
          value={health}
          gradient="bg-gradient-to-br from-emerald-500 to-teal-600"
        />
        <StatCard
          icon={Bot}
          label="Agenten"
          value={agents.length}
          gradient="bg-gradient-to-br from-purple-600 to-violet-700"
        />
        {role === "admin" && (
          <StatCard
            icon={Users}
            label="Benutzer"
            value={users.length}
            gradient="bg-gradient-to-br from-blue-500 to-indigo-600"
          />
        )}
      </div>

      {agents.length > 0 && (
        <div className="bg-card border border-border rounded-xl p-5">
          <h3 className="text-sm font-medium text-foreground mb-3">Masteragenten</h3>
          <div className="space-y-2">
            {masterAgents.map((a) => (
              <div key={a.id} className="flex items-center gap-3 py-2 border-b border-border last:border-0">
                <div className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
                <span className="text-sm text-foreground flex-1">{a.name}</span>
                <span className="text-xs text-muted-foreground">{a.owner}</span>
              </div>
            ))}
            {specialists.length > 0 && (
              <p className="text-xs text-muted-foreground pt-1">
                + {specialists.length} Spezialist{specialists.length !== 1 ? "en" : ""}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
