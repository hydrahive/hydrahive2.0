import { useEffect, useMemo, useState } from "react"
import { Check, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { settingsApi, type EditableSetting } from "@/features/system/settingsApi"
import { AdminFeedback, AdminPanel, AdminToggle, adminInputClass } from "./ui"
import { AdminOverlay } from "./AdminOverlay"

const BOOL_TRUE = new Set(["1", "true", "yes", "on"])
type RowStatus = "idle" | "saving" | "saved" | "error"

function SettingRow({ setting, onSaved }: { setting: EditableSetting; onSaved: (updated: EditableSetting) => void }) {
  const [draft, setDraft] = useState(setting.type === "secret" ? "" : setting.value)
  const [status, setStatus] = useState<RowStatus>("idle")

  async function save(value: string) {
    setStatus("saving")
    try {
      onSaved(await settingsApi.update(setting.key, value))
      setStatus("saved")
      setTimeout(() => setStatus("idle"), 1500)
    } catch {
      setStatus("error")
    }
  }

  const boolOn = BOOL_TRUE.has(setting.value.toLowerCase())
  const original = setting.type === "secret" ? "" : setting.value

  return (
    <div className="grid gap-3 border-b border-[#2a364b] py-3 last:border-0 md:grid-cols-[minmax(0,1fr)_14rem] md:items-start">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium text-[#e8eef8]">{setting.label}</span>
          {setting.overridden && (
            <span className="rounded-[4px] border border-[#69d7ff]/35 bg-[#163248] px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-[#c8f2ff]">GUI</span>
          )}
          {status === "saved" && <Check size={13} className="text-emerald-400" aria-label="Gespeichert" />}
          {status === "saving" && <Loader2 size={13} className="animate-spin text-amber-300" aria-label="Wird gespeichert" />}
          {status === "error" && <span className="text-[11px] text-rose-300">Fehler beim Speichern</span>}
        </div>
        {setting.help && <p className="mt-1 text-xs leading-relaxed text-[#8d9ab0]">{setting.help}</p>}
      </div>

      <div className="w-full">
        {setting.type === "bool" ? (
          <AdminToggle checked={boolOn} onChange={() => save(boolOn ? "0" : "1")} aria-label={setting.label} />
        ) : (
          <input
            type={setting.type === "secret" ? "password" : setting.type === "int" ? "number" : "text"}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onBlur={() => { if (draft !== original) save(draft) }}
            placeholder={setting.type === "secret" && setting.is_set ? "•••••••• (gesetzt)" : ""}
            className={adminInputClass}
          />
        )}
      </div>
    </div>
  )
}

export function SystemSettingsOverlay({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("system")
  const [settings, setSettings] = useState<EditableSetting[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    settingsApi.list()
      .then((response) => setSettings(response.settings))
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Fehler"))
  }, [])

  const groups = useMemo(() => {
    const grouped = new Map<string, EditableSetting[]>()
    for (const setting of settings ?? []) grouped.set(setting.group, [...(grouped.get(setting.group) ?? []), setting])
    return Array.from(grouped.entries())
  }, [settings])

  function onSaved(updated: EditableSetting) {
    setSettings((previous) => previous?.map((setting) => setting.key === updated.key ? updated : setting) ?? previous)
  }

  return (
    <AdminOverlay eyebrow="Admin · System" title={t("settings.title")} onClose={onClose} maxWidthClass="max-w-3xl">
      <div className="space-y-4">
        <p className="text-sm text-[#8d9ab0]">{t("settings.subtitle")}</p>
        {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
        {!settings && !error && <AdminFeedback loading>Systemeinstellungen werden geladen …</AdminFeedback>}
        {groups.map(([group, rows]) => (
          <AdminPanel key={group} title={group} bodyClassName="px-4 py-1">
            {rows.map((setting) => <SettingRow key={setting.key} setting={setting} onSaved={onSaved} />)}
          </AdminPanel>
        ))}
      </div>
    </AdminOverlay>
  )
}
