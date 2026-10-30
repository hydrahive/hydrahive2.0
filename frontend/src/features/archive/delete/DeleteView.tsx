import { Archive, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminFeedback } from "@/features/cockpit/admin/ui"
import { cn } from "@/shared/cn"
import { formatSize } from "../format"
import type { DeleteMode, DeletePreview } from "./api"

export interface DeleteViewProps {
  preview: DeletePreview
  mode: DeleteMode | null
  typed: string
  busy: boolean
  error: string | null
  onMode: (mode: DeleteMode) => void
  onTyped: (value: string) => void
  onStart: () => void
}

/** Inhalt des Lösch-Dialogs: was betroffen ist, zwei Wege, Bestätigung (Spec archiv-system.md, Etappe 2).
 *  „Ins Archiv“ ist vorausgewählt, wenn es geht. „Unwiderruflich“ nie – nur nach Eintippen des Namens. */
export function DeleteView({ preview, mode, typed, busy, error, onMode, onTyped, onStart }: DeleteViewProps) {
  const { t } = useTranslation("archive")
  const a = preview.archive
  const canStart = !busy && (mode === "archive" ? a.possible : mode === "permanent" && typed === preview.name)
  const size = formatSize(preview.size.bytes)
  return (
    <div className="space-y-3 p-4 text-sm text-[#e8eef8]">
      <Affected preview={preview} />
      <p className="text-xs text-[#9aa7bc]">
        {preview.size.complete ? t("delete.size.exact", { size }) : t("delete.size.at_least", { size })}
      </p>
      <div className="space-y-2" role="radiogroup" aria-label={t("delete.choose")}>
        <Choice mode="archive" active={mode === "archive"} disabled={!a.possible} onPick={onMode}
          icon={<Archive size={16} className="mt-0.5 shrink-0 text-[#69d7ff]" />} title={t("delete.archive.title")}>
          <span className="block break-all font-mono text-xs text-[#9aa7bc]">{a.path}</span>
          <span className="block text-xs text-[#9aa7bc]">
            {t("delete.archive.free", { free: formatSize(a.free_bytes) })}
            {a.share && ` · ${t("delete.archive.share", { share: a.share })}`}
          </span>
          {!a.possible && a.reason && <span className="block text-xs text-amber-300">{t(`delete.reason.${a.reason}`)}</span>}
        </Choice>
        <Choice mode="permanent" active={mode === "permanent"} disabled={false} onPick={onMode}
          icon={<Trash2 size={16} className="mt-0.5 shrink-0 text-rose-300" />} title={t("delete.permanent.title")}>
          <span className="block text-xs text-[#9aa7bc]">{t("delete.permanent.explain")}</span>
        </Choice>
      </div>
      {mode === "permanent" && (
        <label className="block text-xs text-rose-200">
          {t("delete.permanent.type_name", { name: preview.name })}
          <input value={typed} onChange={(e) => onTyped(e.target.value)} autoComplete="off" spellCheck={false}
            data-delete-input="name"
            className="mt-1 w-full rounded-[4px] border border-rose-500/30 bg-s-tief px-3 py-2 text-sm text-[#e8eef8]" />
        </label>
      )}
      <AdminFeedback>{t("delete.chats_gone")}</AdminFeedback>
      {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
      <div className="flex justify-end">
        <AdminAction tone={mode === "permanent" ? "danger" : "primary"} data-delete-action="start" disabled={!canStart}
          onClick={onStart}>
          {mode === "permanent" ? t("delete.start_permanent") : t("delete.start_archive")}
        </AdminAction>
      </div>
    </div>
  )
}

function Affected({ preview }: { preview: DeletePreview }) {
  const { t } = useTranslation("archive")
  const stays = Object.entries(preview.stays).filter(([, n]) => (n ?? 0) > 0)
  return (
    <div className="space-y-1 rounded-[4px] border border-s-rand bg-s-innen p-3 text-xs text-[#c9d3e3]">
      {preview.projects.length > 0 && preview.kind === "user" && (
        <p>{t("delete.affected.projects", { names: preview.projects.map((p) => p.name).join(", ") })}</p>
      )}
      {preview.agents.length > 0 && <p>{t("delete.affected.agents", { names: preview.agents.map((x) => x.name).join(", ") })}</p>}
      <p>{t("delete.affected.chats", { count: preview.chats })}</p>
      {preview.mounts_skipped.length > 0 && (
        <p>{t("delete.affected.mounts", { names: preview.mounts_skipped.join(", ") })}</p>
      )}
      {preview.hand_over > 0 && <p>{t("delete.hand_over", { count: preview.hand_over })}</p>}
      {stays.map(([key, n]) => <p key={key} className="text-[#9aa7bc]">{t(`delete.stays.${key}`, { count: n })}</p>)}
    </div>
  )
}

function Choice({ mode, active, disabled, onPick, icon, title, children }: {
  mode: DeleteMode; active: boolean; disabled: boolean; onPick: (m: DeleteMode) => void
  icon: React.ReactNode; title: string; children: React.ReactNode
}) {
  return (
    <button type="button" role="radio" aria-checked={active} data-delete-mode={mode} disabled={disabled}
      onClick={() => onPick(mode)}
      className={cn(
        "flex w-full items-start gap-3 rounded-[4px] border p-3 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-60",
        active ? "border-[#69d7ff]/60 bg-[#163248]" : "border-s-rand bg-s-innen hover:border-s-rand-hover",
      )}>
      {icon}
      <span className="min-w-0 flex-1 space-y-0.5"><span className="block font-bold">{title}</span>{children}</span>
    </button>
  )
}
