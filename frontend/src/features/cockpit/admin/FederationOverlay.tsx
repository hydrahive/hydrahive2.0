import { useState } from "react"
import { useSearchParams } from "react-router-dom"
import { Plus } from "lucide-react"
import { useTranslation } from "react-i18next"
import { WorkstationsPanel } from "@/features/federation/WorkstationsPanel"
import { PeersSection } from "@/features/federation/_PeersSection"
import { ClientConnectionsSection } from "@/features/federation/_ClientConnectionsSection"
import { DataminingInstancesSection } from "@/features/federation/_DataminingInstancesSection"
import { FEDERATION_TABS, parseFederationTab, type FederationTab } from "@/features/federation/federationTabs"
import { CockpitButton } from "../CockpitButton"
import { AdminOverlay } from "./AdminOverlay"
import { ADMIN_OVERLAY_THEME } from "@/shared/brand/boxThemes"

/** Föderation im Admin-Cockpit (/admin?section=federation&tab=…): ein Teil pro Reiter statt einer langen Seite. */
export function FederationOverlay({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("federation")
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = parseFederationTab(searchParams.get("tab"))
  const [showAdd, setShowAdd] = useState(false)

  function selectTab(next: FederationTab) {
    const params = new URLSearchParams(searchParams)
    params.set("tab", next)
    setSearchParams(params, { replace: true })
  }

  return (
    <AdminOverlay theme={ADMIN_OVERLAY_THEME["federation"]}
      eyebrow="Admin"
      title={t("title")}
      onClose={onClose}
      maxWidthClass="max-w-4xl"
      headerActions={tab === "workstations" ? (
        <CockpitButton tone="primary" onClick={() => setShowAdd(true)}>
          <Plus size={12} className="mr-1 inline" />{t("add")}
        </CockpitButton>
      ) : undefined}
    >
      <div className="space-y-4">
        <p className="text-sm text-[#9aa7bc]">{t("subtitle")}</p>
        <div role="tablist" aria-label={t("title")}
          className="grid grid-cols-2 gap-1 rounded-[4px] border border-s-rand bg-s-innen p-1 sm:grid-cols-4">
          {FEDERATION_TABS.map((id) => (
            <button key={id} type="button" role="tab" id={`federation-tab-${id}`}
              aria-selected={id === tab} aria-controls="federation-pane"
              onClick={() => selectTab(id)}
              className={`min-w-0 truncate rounded-[3px] px-2 py-2 text-xs font-bold transition-colors sm:text-sm ${
                id === tab ? "bg-[#1c2940] text-[#69d7ff]" : "text-[#9aa7bc] hover:bg-white/5 hover:text-[#e8eef8]"
              }`}>{t(`tabs.${id}`)}</button>
          ))}
        </div>
        <div id="federation-pane" role="tabpanel" aria-labelledby={`federation-tab-${tab}`}>
          {tab === "workstations" && <WorkstationsPanel showAdd={showAdd} onShowAdd={setShowAdd} />}
          {tab === "peers" && <PeersSection />}
          {tab === "clients" && <ClientConnectionsSection />}
          {tab === "datamining" && <DataminingInstancesSection />}
        </div>
      </div>
    </AdminOverlay>
  )
}
