import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { HelpButton } from "@/i18n/HelpButton"
import { dashboardApi, type DashboardSummary } from "./api"
import { StatsRow } from "./_StatsRow"
import { RecentSessions } from "./_RecentSessions"
import { ServersOverview } from "./_ServersOverview"
import { AgentsList } from "./_AgentsList"

const REFRESH_MS = 30_000

export function DashboardPage() {
  const { t } = useTranslation("dashboard")
  const [data, setData] = useState<DashboardSummary | null>(null)

  useEffect(() => {
    let alive = true
    async function load() {
      try {
        const s = await dashboardApi.summary()
        if (alive) setData(s)
      } catch { /* leise */ }
    }
    load()
    const t = setInterval(load, REFRESH_MS)
    return () => { alive = false; clearInterval(t) }
  }, [])

  return (
    <div className="space-y-5 max-w-6xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">{t("title")}</h1>
          <p className="text-zinc-500 text-sm mt-0.5">{t("subtitle")}</p>
        </div>
        <HelpButton topic="dashboard" />
      </div>

      {data && (
        <>
          <StatsRow stats={data.stats} />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <RecentSessions sessions={data.recent_sessions} />
            <ServersOverview servers={data.servers} />
          </div>

          <AgentsList agents={data.agents} />
        </>
      )}
    </div>
  )
}
