import { CheckCircle2, CloudUpload, RefreshCw, Save, ShieldCheck, XCircle } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminFeedback, AdminField, AdminPanel, AdminStatus, AdminToggle, adminInputClass } from "@/features/cockpit/admin/ui"
import type { ArchiveRemote, RemoteForm, RemoteTestResult } from "./api"
import { formatSize } from "./format"

export interface RemoteViewProps {
  remote: ArchiveRemote
  form: RemoteForm
  testResult: RemoteTestResult | null
  busy: boolean
  error: string | null
  onForm: (form: RemoteForm) => void
  onSave: () => void
  onTest: () => void
  onActive: (active: boolean) => void
  onSync: () => void
}

const FIELDS: (keyof RemoteForm)[] = ["host", "share", "subdir", "user", "password"]

/** Bereich „Externer Server“: Kopie des Archivs aufs NAS (Spec archiv-system.md, Etappe 3). */
export function RemoteView({ remote, form, testResult, busy, error, onForm, onSave, onTest, onActive, onSync }: RemoteViewProps) {
  const { t } = useTranslation("archive")
  const minutes = remote.next_try_in_s != null ? Math.max(1, Math.ceil(remote.next_try_in_s / 60)) : null
  return (
    <div data-archive-section="remote">
      <AdminPanel title={t("remote.title")} description={t("remote.subtitle")} icon={CloudUpload} bodyClassName="space-y-3"
        actions={(
          <AdminStatus tone={remote.active ? "success" : "neutral"} icon={remote.active ? CheckCircle2 : XCircle}>
            {remote.active ? t("remote.state_active") : t("remote.state_inactive")}
          </AdminStatus>
        )}>
        {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
        <div className="grid gap-3 sm:grid-cols-2">
          {FIELDS.map((f) => (
            <AdminField key={f} label={t(`remote.field.${f}`)}
              help={f === "password" && remote.password_set ? t("remote.password_kept") : t(`remote.help.${f}`)}>
              <input className={adminInputClass} name={f} value={form[f]} disabled={busy}
                type={f === "password" ? "password" : "text"} autoComplete={f === "password" ? "new-password" : "off"}
                onChange={(e) => onForm({ ...form, [f]: e.target.value })} />
            </AdminField>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <AdminAction tone="primary" data-remote-action="save" disabled={busy || !form.host || !form.share} onClick={onSave}>
            <Save size={11} /> {t("remote.save")}
          </AdminAction>
          <AdminAction data-remote-action="test" disabled={busy || !remote.configured} onClick={onTest}>
            <ShieldCheck size={11} /> {t("remote.test")}
          </AdminAction>
          <AdminAction tone="ghost" data-remote-action="sync" disabled={busy || !remote.active} onClick={onSync}>
            <RefreshCw size={11} /> {t("remote.sync")}
          </AdminAction>
        </div>
        {testResult && (testResult.ok
          ? <AdminFeedback tone="success">{t("remote.test_ok", { free: formatSize(testResult.free_bytes) })}</AdminFeedback>
          : <AdminFeedback tone="danger">{t(`remote.error.${testResult.error}`, { defaultValue: t("remote.error.unexpected") })}</AdminFeedback>)}
        <AdminToggle label={t("remote.switch")} checked={remote.active} data-remote-action="active"
          disabled={busy || !remote.tested} onChange={(e) => onActive(e.target.checked)} />
        {!remote.tested && remote.configured && <p className="text-[11px] text-[#8d9ab0]">{t("remote.test_first")}</p>}
        {remote.active && (
          <dl className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 text-sm">
            <dt className="text-[#8d9ab0]">{t("remote.on_server")}</dt>
            <dd className="text-right text-[#e8eef8]">{remote.on_server}</dd>
            <dt className="text-[#8d9ab0]">{t("remote.waiting")}</dt>
            <dd className="text-right text-[#e8eef8]" data-remote-waiting={remote.waiting}>{remote.waiting}</dd>
          </dl>
        )}
        {remote.active && remote.waiting > 0 && remote.last_error && (
          <AdminFeedback tone="warning">
            {t(`remote.error.${remote.last_error}`, { defaultValue: t("remote.error.unexpected") })}{" "}
            {minutes != null && t("remote.next_try", { minutes })}
          </AdminFeedback>
        )}
        <p className="text-[11px] leading-relaxed text-[#8d9ab0]">{t("remote.hint")}</p>
      </AdminPanel>
    </div>
  )
}
