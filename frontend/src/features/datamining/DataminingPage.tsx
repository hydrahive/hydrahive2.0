import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Pickaxe } from "lucide-react"
import { LiveFeedTab } from "./LiveFeedTab"
import { SearchTab } from "./SearchTab"
import { SessionsTab } from "./SessionsTab"
import { GraphTab } from "./GraphTab"
import { StatsTab } from "./StatsTab"
import { dataminingApi } from "./api"
import { EmbedStatusBar, type EmbedStatus } from "./_EmbedStatusBar"
import { DataminingAdminBar } from "./_DataminingAdminBar"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { HelpButton } from "@/i18n/HelpButton"

const TABS = ["feed", "search", "sessions", "stats", "graph"] as const
type Tab = typeof TABS[number]

export function DataminingPage() {
  const { t } = useTranslation("datamining")
  const [tab, setTab] = useState<Tab>("feed")
  const [embedStatus, setEmbedStatus] = useState<EmbedStatus | null>(null)
  const isAdmin = useAuthStore((st) => st.role) === "admin"

  useEffect(() => {
    dataminingApi.embedStatus().then(setEmbedStatus).catch(() => {})
    const iv = setInterval(() => {
      dataminingApi.embedStatus().then(setEmbedStatus).catch(() => {})
    }, 8000)
    return () => clearInterval(iv)
  }, [])


  return (
    <div className="space-y-4 max-w-4xl">
      <div className="flex items-center gap-3">
        <Pickaxe className="text-amber-400" size={20} />
        <div>
          <h1 className="text-xl font-semibold text-zinc-100">{t("title")}</h1>
          <p className="text-xs text-zinc-500 mt-0.5">{t("subtitle")}</p>
        </div>
        <HelpButton topic="datamining" />
      </div>

      <div className="flex gap-1 border-b border-white/[6%]">
        {TABS.map((id) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === id
                ? "text-amber-300 border-amber-400"
                : "text-zinc-500 border-transparent hover:text-zinc-300"
            }`}
          >
            {t(`tabs.${id}`)}
          </button>
        ))}
      </div>

      {embedStatus?.active && embedStatus && (
        <EmbedStatusBar
          status={embedStatus}
          onBackfill={!isAdmin ? undefined : () =>
            dataminingApi.triggerBackfill()
              .then(() => dataminingApi.embedStatus().then(setEmbedStatus).catch(() => {}))
              .catch(() => {})
          }
          onReset={!isAdmin ? undefined : () =>
            dataminingApi.resetEmbeddings()
              .then(() => dataminingApi.embedStatus().then(setEmbedStatus).catch(() => {}))
              .catch(() => {})
          }
          onRechunk={!isAdmin ? undefined : () =>
            dataminingApi.triggerRechunk()
              .then(() => dataminingApi.embedStatus().then(setEmbedStatus).catch(() => {}))
              .catch(() => {})
          }
        />
      )}

      {isAdmin && <DataminingAdminBar />}

      {tab === "feed" && <LiveFeedTab active={tab === "feed"} />}
      {tab === "search" && <SearchTab />}
      {tab === "sessions" && <SessionsTab active={tab === "sessions"} />}
      {tab === "stats" && <StatsTab active={tab === "stats"} />}
      {tab === "graph" && <GraphTab />}
    </div>
  )
}
