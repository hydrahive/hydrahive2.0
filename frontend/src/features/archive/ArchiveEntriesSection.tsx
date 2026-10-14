import { Archive } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminFeedback, AdminPanel, adminInputClass } from "@/features/cockpit/admin/ui"
import { remoteStateOf, type ArchiveEntry, type ArchiveKind } from "./api"
import { formatSize } from "./format"

const KINDS: ArchiveKind[] = ["agents", "projects", "users", "backups", "uploads"]

interface Props {
  entries: ArchiveEntry[]
  kind: ArchiveKind | null
  onKind: (kind: ArchiveKind | null) => void
}

function when(entry: ArchiveEntry): string {
  const iso = entry.created_at ?? new Date(entry.mtime * 1000).toISOString()
  return iso.slice(0, 16).replace("T", " ")
}

/** Archivierte Elemente (nur lesen in Etappe 1). Von Hand über Samba abgelegte Dateien sind markiert. */
export function ArchiveEntriesSection({ entries, kind, onKind }: Props) {
  const { t } = useTranslation("archive")
  return (
    <div data-archive-section="entries">
      <AdminPanel
        title={t("entries.title")}
        description={t("entries.subtitle")}
        icon={Archive}
        actions={(
          <select className={adminInputClass} value={kind ?? ""} aria-label={t("entries.filter")}
            onChange={(e) => onKind((e.target.value || null) as ArchiveKind | null)}>
            <option value="">{t("entries.all")}</option>
            {KINDS.map((k) => <option key={k} value={k}>{t(`kind.${k}`)}</option>)}
          </select>
        )}
        bodyClassName="space-y-2"
      >
        {entries.length === 0 ? (
          <AdminFeedback>{t("entries.empty")}</AdminFeedback>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-[#8d9ab0]">
                <tr>
                  <th className="py-1 pr-3 font-medium">{t("entries.col_name")}</th>
                  <th className="py-1 pr-3 font-medium">{t("entries.col_kind")}</th>
                  <th className="py-1 pr-3 font-medium">{t("entries.col_owner")}</th>
                  <th className="py-1 pr-3 font-medium">{t("entries.col_reason")}</th>
                  <th className="py-1 pr-3 font-medium">{t("entries.col_date")}</th>
                  <th className="py-1 pr-3 font-medium">{t("entries.col_remote")}</th>
                  <th className="py-1 text-right font-medium">{t("entries.col_size")}</th>
                </tr>
              </thead>
              <tbody className="text-[#e8eef8]">
                {entries.map((e) => (
                  <tr key={e.path} className="border-t border-[#1e2738]"
                    {...(e.manual ? { "data-archive-manual": e.path } : {})}>
                    <td className="max-w-[18rem] truncate py-1.5 pr-3" title={e.path}>
                      {e.manual ? <span className="font-mono">{e.path}</span> : e.name}
                    </td>
                    <td className="py-1.5 pr-3">{e.kind ? t(`kind.${e.kind}`, { defaultValue: e.kind }) : "—"}</td>
                    <td className="py-1.5 pr-3">{e.owner ?? "—"}</td>
                    <td className="py-1.5 pr-3">
                      {e.manual ? t("entries.manual") : t(`reason.${e.reason}`, { defaultValue: e.reason ?? "—" })}
                    </td>
                    <td className="whitespace-nowrap py-1.5 pr-3">{when(e)}</td>
                    <td className="whitespace-nowrap py-1.5 pr-3" data-entry-remote={remoteStateOf(e)}>
                      {t(`entries.remote.${remoteStateOf(e)}`)}
                    </td>
                    <td className="whitespace-nowrap py-1.5 text-right">{formatSize(e.size)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </AdminPanel>
    </div>
  )
}
