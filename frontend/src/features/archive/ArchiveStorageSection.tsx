import { ArrowRightLeft, CheckCircle2, HardDrive, Trash2, XCircle } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminFeedback, AdminPanel, AdminStatus } from "@/features/cockpit/admin/ui"
import type { ArchiveMove, ArchiveStorage } from "./api"
import { MoveProgress } from "./MoveProgress"
import { formatSize } from "./format"

interface Props {
  storage: ArchiveStorage
  move?: ArchiveMove
  onEmptyTrash: () => void
  onChangeLocation: () => void
}

/** Speicherort: wo das Archiv liegt (Platte, freier Platz), wie voll, Papierkorb. HydraHive richtet ihn selbst ein. */
export function ArchiveStorageSection({ storage, move, onEmptyTrash, onChangeLocation }: Props) {
  const { t } = useTranslation("archive")
  const ok = storage.exists && storage.writable
  return (
    <div data-archive-section="storage">
      <AdminPanel
        title={t("storage.title")}
        description={t("storage.subtitle")}
        icon={HardDrive}
        actions={(
          <AdminStatus tone={ok ? "success" : "warning"} icon={ok ? CheckCircle2 : XCircle}>
            {ok ? t("storage.ok") : storage.exists ? t("storage.readonly") : t("storage.missing")}
          </AdminStatus>
        )}
        bodyClassName="space-y-3"
      >
        {storage.setup_error && (
          <AdminFeedback tone="danger">
            {t("storage.setup_failed")} <span className="font-mono">{storage.setup_error}</span>
          </AdminFeedback>
        )}
        <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-2 text-xs">
          <span className="text-[#8d9ab0]">{t("storage.target")}</span>
          <span className="text-[#e8eef8]">{t("storage.target_local")}</span>
          <span className="text-[#8d9ab0]">{t("storage.path")}</span>
          <span className="break-all font-mono text-[#e8eef8]">{storage.path}</span>
          <span className="text-[#8d9ab0]">{t("storage.disk")}</span>
          <span className="break-all font-mono text-[#e8eef8]" data-archive-mount={storage.mount}>{storage.mount}</span>
          <span className="text-[#8d9ab0]">{t("storage.free")}</span>
          <span className="text-[#e8eef8]">{formatSize(storage.free_bytes)}</span>
          <span className="text-[#8d9ab0]">{t("storage.count")}</span>
          <span className="text-[#e8eef8]" data-archive-count={storage.count}>
            {t("storage.count_value", { count: storage.count, manual: storage.manual_count })}
          </span>
          <span className="text-[#8d9ab0]">{t("storage.used")}</span>
          <span className="text-[#e8eef8]">{formatSize(storage.used_bytes)}</span>
          <span className="text-[#8d9ab0]">{t("storage.trash")}</span>
          <span className="flex items-center gap-2 text-[#e8eef8]">
            {formatSize(storage.trash_bytes)}
            <AdminAction
              tone="danger"
              className="px-2"
              data-archive-action="empty-trash"
              disabled={storage.trash_bytes === 0}
              onClick={onEmptyTrash}
            >
              <Trash2 size={11} /> {t("storage.empty_trash")}
            </AdminAction>
          </span>
        </div>
        <MoveProgress move={move} />
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-[11px] leading-relaxed text-[#8d9ab0]">{storage.is_default ? t("storage.default_hint") : ""}</p>
          <AdminAction data-archive-action="change-location" disabled={!!move?.running} onClick={onChangeLocation}>
            <ArrowRightLeft size={11} /> {t("storage.change")}
          </AdminAction>
        </div>
      </AdminPanel>
    </div>
  )
}
