import { CheckCircle2, Download, Loader2, Puzzle, TriangleAlert, X, XCircle } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminCodeBlock, AdminFeedback, AdminPanel, AdminStatus } from "@/features/cockpit/admin/ui"
import type { AddonId, AddonItem } from "./addonsApi"
import type { AddonPhase } from "./useAddons"

export interface AddonsViewProps {
  items: AddonItem[] | null
  running: string | null
  target: AddonId | null
  phase: AddonPhase
  log: string[]
  error: string | null
  onAsk: (id: AddonId) => void
  onConfirm: () => void
  onClose: () => void
}

/** Darstellung der Karte „Zusatz-Module“ (nur Props, ohne Datenzugriff – testbar). */
export function AddonsView({ items, running, target, phase, log, error, onAsk, onConfirm, onClose }: AddonsViewProps) {
  const { t } = useTranslation("system")
  const { t: tCommon } = useTranslation("common")
  const busy = running !== null || phase === "running" || phase === "confirm"
  const current = items?.find((i) => i.id === target) ?? null
  const missing = current ? current.requires.filter((r) => !items?.find((i) => i.id === r)?.installed) : []

  return (
    <AdminPanel title={t("addons.title")} description={t("addons.subtitle")} icon={Puzzle} bodyClassName="space-y-3">
      <ul className="divide-y divide-white/5">
        {(items ?? []).map((item) => (
          <li key={item.id} data-addon-row={item.id} className="flex flex-wrap items-center gap-3 py-2">
            <div className="min-w-0 flex-1">
              <p className="text-sm text-[#d4deeb]">{t(`addons.name.${item.id}`)}</p>
              <p className="text-xs text-[#8d9ab0]">{t(`addons.desc.${item.id}`)}</p>
              {item.hint && (
                <p className="mt-1 text-xs text-amber-300/90">
                  <TriangleAlert size={11} className="mr-1 inline" />{t(`addons.hint_${item.hint}`)}
                </p>
              )}
            </div>
            {running === item.id ? (
              <AdminStatus tone="warning" icon={Loader2} pulse>{t("addons.running_badge")}</AdminStatus>
            ) : item.installed ? (
              <AdminStatus tone="success" icon={CheckCircle2}>{t("addons.installed")}</AdminStatus>
            ) : item.hint === "mac" ? (
              <AdminStatus tone="neutral" icon={XCircle}>{t("addons.not_installed")}</AdminStatus>
            ) : (
              <>
                <AdminStatus tone="neutral" icon={XCircle}>{t("addons.not_installed")}</AdminStatus>
                <AdminAction data-addon={item.id} tone="primary" disabled={busy} onClick={() => onAsk(item.id)}
                  title={busy ? t("addons.busy_title") : undefined}>
                  <Download size={11} /> {t("addons.install")}
                </AdminAction>
              </>
            )}
          </li>
        ))}
      </ul>

      {phase === "confirm" && current && (
        <div className="space-y-3">
          <AdminFeedback tone="warning">
            <p>{t("addons.confirm", { name: t(`addons.name.${current.id}`) })}</p>
            {missing.length > 0 && (
              <p className="mt-1">{t("addons.confirm_requires", { names: missing.map((m) => t(`addons.name.${m}`)).join(", ") })}</p>
            )}
            {(current.restarts_service || missing.some((m) => items?.find((i) => i.id === m)?.restarts_service)) && (
              <p className="mt-1 text-[#8d9ab0]">{t("addons.confirm_restart")}</p>
            )}
          </AdminFeedback>
          <div className="flex justify-end gap-2">
            <AdminAction onClick={onClose}>{tCommon("actions.cancel")}</AdminAction>
            <AdminAction tone="primary" onClick={onConfirm}>{t("addons.confirm_button")}</AdminAction>
          </div>
        </div>
      )}

      {(phase === "running" || phase === "done" || phase === "failed") && target && (
        <div className="space-y-2">
          <div className="flex items-start gap-2">
            <div className="min-w-0 flex-1">
              {phase === "running" && (
                <AdminFeedback tone="warning" loading>{t("addons.running", { name: t(`addons.name.${target}`) })}</AdminFeedback>
              )}
              {phase === "done" && <AdminFeedback tone="success">{t("addons.done", { name: t(`addons.name.${target}`) })}</AdminFeedback>}
              {phase === "failed" && <AdminFeedback tone="danger">{error ?? t("addons.failed")}</AdminFeedback>}
            </div>
            {phase !== "running" && (
              <AdminAction tone="ghost" className="px-2" aria-label={tCommon("actions.close")}
                title={tCommon("actions.close")} onClick={onClose}>
                <X size={11} />
              </AdminAction>
            )}
          </div>
          <div className="max-h-[260px] min-h-[120px] overflow-auto">
            <AdminCodeBlock className="min-h-[120px]">{log.length > 0 ? log.join("") : t("addons.log_empty")}</AdminCodeBlock>
          </div>
        </div>
      )}
    </AdminPanel>
  )
}
