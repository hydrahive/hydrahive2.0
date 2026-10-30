import { Archive, HardDriveDownload } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminFeedback, AdminPanel, adminInputClass } from "@/features/cockpit/admin/ui"
import { remoteStateOf, type ArchiveEntry, type ArchiveKind } from "./api"
import { formatSize } from "./format"

const KINDS: ArchiveKind[] = ["agents", "projects", "users", "backups", "uploads"]

interface Props {
  entries: ArchiveEntry[]
  kind: ArchiveKind | null
  onKind: (kind: ArchiveKind | null) => void
  /** Etappe 3b: lokale Kopie eines Pakets löschen, das geprüft auf dem Server liegt. */
  onDropLocal?: (entry: ArchiveEntry) => void
}

/** Nur Pakete, nie von Hand Abgelegtes (Till, 14.10.) – und nur, wenn die Kopie geprüft auf dem Server liegt. */
function canDrop(e: ArchiveEntry): boolean {
  return !e.manual && e.local !== false && remoteStateOf(e) === "server"
}

function when(entry: ArchiveEntry): string {
  const iso = entry.created_at ?? new Date(entry.mtime * 1000).toISOString()
  return iso.slice(0, 16).replace("T", " ")
}

/** Archivierte Elemente. Von Hand über Samba abgelegte Dateien sind markiert. */
export function ArchiveEntriesSection({ entries, kind, onKind, onDropLocal }: Props) {
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
              <thead className="text-[#9aa7bc]">
                <tr>
                  <th className="py-1 pr-3 font-medium">{t("entries.col_name")}</th>
                  <th className="py-1 pr-3 font-medium">{t("entries.col_kind")}</th>
                  <th className="py-1 pr-3 font-medium">{t("entries.col_owner")}</th>
                  <th className="py-1 pr-3 font-medium">{t("entries.col_reason")}</th>
                  <th className="py-1 pr-3 font-medium">{t("entries.col_date")}</th>
                  <th className="py-1 pr-3 font-medium">{t("entries.col_remote")}</th>
                  <th className="py-1 pr-3 text-right font-medium">{t("entries.col_size")}</th>
                  {onDropLocal && <th className="py-1 font-medium"><span className="sr-only">{t("entries.col_actions")}</span></th>}
                </tr>
              </thead>
              <tbody className="text-[#e8eef8]">
                {entries.map((e) => (
                  <tr key={e.path} className="border-t border-s-rand"
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
                    <td className="whitespace-nowrap py-1.5 pr-3 text-right">{formatSize(e.size)}</td>
                    {onDropLocal && (
                      <td className="whitespace-nowrap py-1.5 text-right">
                        {canDrop(e) && (
                          <AdminAction tone="ghost" data-entry-drop={e.path} title={t("entries.drop_local")}
                            onClick={() => onDropLocal(e)}>
                            <HardDriveDownload size={11} /> {t("entries.drop_local")}
                          </AdminAction>
                        )}
                      </td>
                    )}
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
