import { Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminFeedback, AdminPanel } from "@/features/cockpit/admin/ui"
import type { OrphanScan } from "./api"
import { formatSize } from "./format"

interface Props {
  scan: OrphanScan | null
  busy: boolean
  onCleanup: () => void
}

/** Bereich „Waisen“: Arbeitsordner ohne Agent und Agenten ohne Projekt. Leere gehen weg, alles mit Inhalt ins Archiv. */
export function OrphansView({ scan, busy, onCleanup }: Props) {
  const { t } = useTranslation("archive")
  const empty = scan?.workspaces.filter((w) => w.empty) ?? []
  const full = scan?.workspaces.filter((w) => !w.empty) ?? []
  const agents = scan?.agents ?? []
  const fullBytes = full.reduce((sum, w) => sum + w.size, 0)
  const nothing = !!scan && empty.length + full.length + agents.length === 0
  return (
    <div data-archive-section="orphans">
      <AdminPanel title={t("orphans.title")} description={t("orphans.subtitle")} icon={Sparkles}
        bodyClassName="space-y-2"
        actions={(
          <AdminAction tone="primary" data-orphans-action="cleanup" disabled={!scan || nothing || busy}
            onClick={onCleanup}>
            {t("orphans.cleanup")}
          </AdminAction>
        )}>
        {!scan && <AdminFeedback loading>{t("orphans.loading")}</AdminFeedback>}
        {nothing && <AdminFeedback tone="success">{t("orphans.none")}</AdminFeedback>}
        {scan && !nothing && (
          <dl className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 text-sm">
            <dt className="text-[#8d9ab0]">{t("orphans.empty")}</dt>
            <dd className="text-right text-[#e8eef8]" data-orphans-empty={empty.length}>{empty.length}</dd>
            <dt className="text-[#8d9ab0]">{t("orphans.full")}</dt>
            <dd className="text-right text-[#e8eef8]" data-orphans-full={full.length}>
              {full.length} · {formatSize(fullBytes)}
            </dd>
            <dt className="text-[#8d9ab0]">{t("orphans.agents")}</dt>
            <dd className="text-right text-[#e8eef8]" data-orphans-agents={agents.length}>{agents.length}</dd>
          </dl>
        )}
        {scan && !scan.complete && <p className="text-xs text-[#8d9ab0]">{t("orphans.at_least")}</p>}
        {scan && !nothing && <p className="text-xs text-[#8d9ab0]">{t("orphans.what_happens")}</p>}
      </AdminPanel>
    </div>
  )
}
