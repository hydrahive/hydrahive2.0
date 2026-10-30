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
import { AdminTabs } from "./ui"
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
        <AdminTabs label={t("title")} idPrefix="federation" active={tab} onSelect={selectTab}
          tabs={FEDERATION_TABS.map((id) => ({ id, label: t(`tabs.${id}`) }))}>
          {tab === "workstations" && <WorkstationsPanel showAdd={showAdd} onShowAdd={setShowAdd} />}
          {tab === "peers" && <PeersSection />}
          {tab === "clients" && <ClientConnectionsSection />}
          {tab === "datamining" && <DataminingInstancesSection />}
        </AdminTabs>
      </div>
    </AdminOverlay>
  )
}
