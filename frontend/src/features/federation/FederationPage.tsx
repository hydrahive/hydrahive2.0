import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Globe, Plus } from "lucide-react"
import { HelpButton } from "@/i18n/HelpButton"
import { WorkstationsPanel } from "./WorkstationsPanel"
import { ClientConnectionsSection } from "./_ClientConnectionsSection"
import { PeersSection } from "./_PeersSection"
import { DataminingInstancesSection } from "./_DataminingInstancesSection"

export function FederationPage() {
  const { t } = useTranslation("federation")
  const [showAdd, setShowAdd] = useState(false)

  return (
    <div className="space-y-4 max-w-3xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Globe className="text-violet-400" size={20} />
          <div>
            <h1 className="text-xl font-semibold text-zinc-100">{t("title")}</h1>
            <p className="text-xs text-zinc-500 mt-0.5">{t("subtitle")}</p>
          </div>
          <HelpButton topic="federation" />
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm bg-violet-600 hover:bg-violet-500 text-white transition-colors"
        >
          <Plus size={14} />
          {t("add")}
        </button>
      </div>

      <WorkstationsPanel showAdd={showAdd} onShowAdd={setShowAdd} />

      <div className="border-t border-white/[4%] pt-4">
        <PeersSection />
      </div>

      <div className="border-t border-white/[4%] pt-4">
        <ClientConnectionsSection />
      </div>

      <div className="border-t border-white/[4%] pt-4">
        <DataminingInstancesSection />
      </div>
    </div>
  )
}
