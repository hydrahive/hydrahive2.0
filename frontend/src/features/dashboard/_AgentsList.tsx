import { Bot, Crown, Wrench } from "lucide-react"
import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"
import type { DashboardAgent } from "./api"

const TYPE_ICON = { master: Crown, project: Bot, specialist: Wrench }
const TYPE_TONE: Record<string, string> = {
  master: "text-amber-300",
  project: "text-violet-300",
  specialist: "text-sky-300",
}

interface Props {
  agents: DashboardAgent[]
}

export function AgentsList({ agents }: Props) {
  const { t } = useTranslation("dashboard")
  if (agents.length === 0) {
    return (
      <div className="rounded-xl border border-white/[8%] bg-white/[3%] p-4">
        <h3 className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500 mb-2">
          {t("sections.agents")}
        </h3>
        <p className="text-xs text-zinc-500 py-4 text-center">{t("sections.agents_empty")}</p>
      </div>
    )
  }
  const groups = (["master", "project", "specialist"] as const).map((type) => ({
    type,
    items: agents.filter((a) => a.type === type),
  })).filter((g) => g.items.length > 0)
  return (
    <div className="rounded-xl border border-white/[8%] bg-white/[3%] p-4 space-y-3">
      <h3 className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">
        {t("sections.agents")}
      </h3>
      {groups.map((g) => {
        const Icon = TYPE_ICON[g.type]
        return (
          <div key={g.type} className="space-y-1">
            <p className={`flex items-center gap-1.5 text-[10px] font-medium ${TYPE_TONE[g.type]}`}>
              <Icon size={11} /> {t(`agent_types.${g.type}`)} ({g.items.length})
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-1">
              {g.items.map((a) => (
                <Link key={a.id} to="/agents"
                  className="flex items-center gap-2 px-2 py-1 rounded-md hover:bg-white/[4%] transition-colors">
                  <span className="text-xs text-zinc-200 truncate">{a.name}</span>
                  {a.owner && <span className="text-[10px] text-zinc-600 ml-auto">{a.owner}</span>}
                </Link>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
