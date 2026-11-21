import { useTranslation } from "react-i18next"
import { CatalogSwitch } from "./_CatalogSwitch"
import { INTERVAL_MAX, INTERVAL_MIN, isDirty, parseInterval, toggleIn, type CatalogDraft } from "./_catalogSync"
import type { CatalogSettings } from "./types"

interface Props {
  settings: CatalogSettings
  draft: CatalogDraft
  users: string[]
  projects: { id: string; name: string }[]
  saving: boolean
  saved: boolean
  error: string
  onChange: (next: CatalogDraft) => void
  onSave: () => void
  onReset: () => void
}

const chip = (on: boolean) =>
  `px-2 py-0.5 rounded-md text-[11px] border transition-colors ${on
    ? "bg-violet-600/30 border-violet-500/50 text-violet-200"
    : "bg-zinc-950/40 border-white/[6%] text-zinc-500 hover:text-zinc-300"}`

// Formular des Abschnitts „Katalog-Sync“ (rein darstellend, Zustand liegt in CatalogSyncSection).
export function CatalogSyncForm(p: Props) {
  const { t } = useTranslation("federation")
  const { settings, draft } = p
  const range = { min: INTERVAL_MIN, max: INTERVAL_MAX }
  const intervalOk = parseInterval(draft.interval) !== null
  const dirty = isDirty(draft, settings)
  const fmt = (v: string | null) => (v ? new Date(v).toLocaleString() : t("catalog.never"))

  return (
    <div className="rounded-lg border border-white/[5%] bg-zinc-900/60 p-3 space-y-3">
      <CatalogSwitch
        checked={draft.enabled}
        label={t("catalog.sync_toggle")}
        hint={t("catalog.sync_hint")}
        onChange={enabled => p.onChange({ ...draft, enabled })}
      />

      <div className="text-[11px] space-y-0.5" data-part="hub">
        <span className="text-zinc-400">{t("catalog.hub_label")} </span>
        {settings.hub ? (
          <span className="text-zinc-200">
            {settings.hub.name}
            {settings.hub.status !== "active" && <span className="text-amber-400"> ({t("catalog.hub_inactive")})</span>}
          </span>
        ) : (
          <span className="text-zinc-500">{t("catalog.hub_none")}</span>
        )}
        {settings.accepting_from.length > 0 && (
          <p className="text-zinc-400">
            {t("catalog.accepting_label")} <span className="text-zinc-200">{settings.accepting_from.map(a => a.name).join(", ")}</span>
          </p>
        )}
      </div>

      <div className="space-y-1">
        <label className="block text-[11px] text-zinc-400" htmlFor="catalog-interval">{t("catalog.interval_label")}</label>
        <input
          id="catalog-interval" inputMode="numeric" value={draft.interval}
          onChange={e => p.onChange({ ...draft, interval: e.target.value })}
          aria-invalid={!intervalOk}
          className={`w-28 rounded-lg bg-zinc-950/60 border px-2.5 py-1 text-xs text-zinc-200 ${intervalOk ? "border-white/[8%]" : "border-red-500/60"}`}
        />
        <p className={`text-[11px] ${intervalOk ? "text-zinc-500" : "text-red-400"}`}>
          {intervalOk ? t("catalog.interval_hint", range) : t("catalog.interval_invalid", range)}
        </p>
      </div>

      <div className="space-y-1.5">
        <p className="text-[11px] text-zinc-400">{t("catalog.users_label")}</p>
        <div className="flex flex-wrap gap-1.5">
          {p.users.length === 0 && <span className="text-[11px] text-zinc-500">{t("catalog.users_empty")}</span>}
          {p.users.map(u => (
            <button key={u} type="button" aria-pressed={draft.users.includes(u)} className={chip(draft.users.includes(u))}
              onClick={() => p.onChange({ ...draft, users: toggleIn(draft.users, u) })}>{u}</button>
          ))}
        </div>
        {draft.users.length === 0 && <p className="text-[11px] text-zinc-500">{t("catalog.users_none_selected")}</p>}
      </div>

      <div className="space-y-1.5">
        <p className="text-[11px] text-zinc-400">{t("catalog.projects_label")}</p>
        <div className="flex flex-wrap gap-1.5 max-h-28 overflow-y-auto">
          {p.projects.length === 0 && <span className="text-[11px] text-zinc-500">{t("catalog.projects_empty")}</span>}
          {p.projects.map(pr => (
            <button key={pr.id} type="button" aria-pressed={draft.excluded_projects.includes(pr.id)}
              className={chip(draft.excluded_projects.includes(pr.id))}
              onClick={() => p.onChange({ ...draft, excluded_projects: toggleIn(draft.excluded_projects, pr.id) })}>{pr.name}</button>
          ))}
        </div>
      </div>

      <div className="space-y-0.5 border-t border-white/[4%] pt-2.5 text-[11px]" data-part="status">
        <p className="text-zinc-400">{t("catalog.status_label")}</p>
        <p className="text-zinc-500">{t("catalog.last_ok")} <span className="text-zinc-300">{fmt(settings.last_ok_at)}</span></p>
        <p className="text-zinc-500">{t("catalog.last_push")} <span className="text-zinc-300">{fmt(settings.last_push_at)}</span></p>
        {settings.last_error && <p className="text-red-400">{t("catalog.last_error")} {settings.last_error}</p>}
      </div>

      <div className="flex items-center gap-2">
        <button type="button" onClick={p.onSave} disabled={!dirty || !intervalOk || p.saving}
          className="px-2.5 py-1 rounded-lg text-xs bg-violet-700 hover:bg-violet-600 disabled:opacity-40 text-white">
          {p.saving ? t("catalog.saving") : t("catalog.save")}
        </button>
        {dirty && (
          <button type="button" onClick={p.onReset} className="px-2.5 py-1 rounded-lg text-xs text-zinc-400 hover:text-zinc-200">
            {t("catalog.reset")}
          </button>
        )}
        {p.saved && !dirty && <span className="text-[11px] text-emerald-400">{t("catalog.saved")}</span>}
      </div>
      {p.error && <p className="text-xs text-red-400">{p.error}</p>}
    </div>
  )
}
