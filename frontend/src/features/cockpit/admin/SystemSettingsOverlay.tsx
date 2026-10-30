import { useEffect, useMemo, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { Check, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { settingsApi, type EditableSetting } from "@/features/system/settingsApi"
import { AdminFeedback, AdminPanel, AdminTabs, AdminToggle, adminInputClass } from "./ui"
import { parseGroup, settingGroups } from "./settingsTabs"
import { AdminOverlay } from "./AdminOverlay"
import { ADMIN_OVERLAY_THEME } from "@/shared/brand/boxThemes"

const BOOL_TRUE = new Set(["1", "true", "yes", "on"])
type RowStatus = "idle" | "saving" | "saved" | "error"

interface RowProps {
  setting: EditableSetting
  onSaved: (updated: EditableSetting) => void
  /** Meldet fehlgeschlagenes (true) bzw. gelungenes (false) Speichern – für den Punkt am Reiter. */
  onFailed: (key: string, failed: boolean) => void
}

function SettingRow({ setting, onSaved, onFailed }: RowProps) {
  const [draft, setDraft] = useState(setting.type === "secret" ? "" : setting.value)
  const [status, setStatus] = useState<RowStatus>("idle")

  async function save(value: string) {
    setStatus("saving")
    try {
      onSaved(await settingsApi.update(setting.key, value))
      onFailed(setting.key, false)
      setStatus("saved")
      setTimeout(() => setStatus("idle"), 1500)
    } catch {
      onFailed(setting.key, true)
      setStatus("error")
    }
  }

  const boolOn = BOOL_TRUE.has(setting.value.toLowerCase())
  const original = setting.type === "secret" ? "" : setting.value

  return (
    <div className="grid gap-3 border-b border-s-rand py-3 last:border-0 md:grid-cols-[minmax(0,1fr)_14rem] md:items-start">
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
        {setting.help && <p className="mt-1 text-xs leading-relaxed text-[#9aa7bc]">{setting.help}</p>}
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

  const [failed, setFailed] = useState<ReadonlySet<string>>(new Set())
  function markFailed(key: string, isFailed: boolean) {
    setFailed((prev) => {
      if (prev.has(key) === isFailed) return prev
      const next = new Set(prev)
      if (isFailed) next.add(key)
      else next.delete(key)
      return next
    })
  }

  function onSaved(updated: EditableSetting) {
    setSettings((previous) => previous?.map((setting) => setting.key === updated.key ? updated : setting) ?? previous)
  }

  return (
    <AdminOverlay theme={ADMIN_OVERLAY_THEME["system-settings"]} eyebrow="Admin · System" title={t("settings.title")} onClose={onClose} maxWidthClass="max-w-3xl">
      <div className="space-y-4">
        <p className="text-sm text-[#9aa7bc]">{t("settings.subtitle")}</p>
        {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
        {!settings && !error && <AdminFeedback loading>Systemeinstellungen werden geladen …</AdminFeedback>}
        {settings && <SettingsView settings={settings} failed={failed} onSaved={onSaved} onFailed={markFailed} />}
      </div>
    </AdminOverlay>
  )
}

interface ViewProps {
  settings: EditableSetting[]
  failed: ReadonlySet<string>
  onSaved: (updated: EditableSetting) => void
  onFailed: (key: string, failed: boolean) => void
}

/** Reiter je Gruppe (Plan admin-reiter-einstellungen). Adresse `gruppe=`, nicht `tab=`: das Fenster liegt oft über
 *  dem System-Fenster, dessen Reiter in `tab=` steht. */
export function SettingsView({ settings, failed, onSaved, onFailed }: ViewProps) {
  const { t } = useTranslation("system")
  const groups = useMemo(() => settingGroups(settings), [settings])
  const [searchParams, setSearchParams] = useSearchParams()
  const active = parseGroup(groups.map((g) => g.slug), searchParams.get("gruppe"))
  const current = groups.find((g) => g.slug === active)
  function selectGroup(slug: string) {
    const params = new URLSearchParams(searchParams)
    params.set("gruppe", slug)
    setSearchParams(params, { replace: true })
  }
  if (!current || !active) return null
  return (
    <AdminTabs label={t("settings.title")} idPrefix="settings" active={active} onSelect={selectGroup} grid
      tabs={groups.map((g) => ({ id: g.slug, label: g.name, count: g.settings.length,
        dot: g.settings.some((x) => failed.has(x.key)) }))}>
      <AdminPanel title={current.name} bodyClassName="px-4 py-1">
        {current.settings.map((setting) => (
          <SettingRow key={setting.key} setting={setting} onSaved={onSaved} onFailed={onFailed} />
        ))}
      </AdminPanel>
    </AdminTabs>
  )
}
