import { useEffect, useMemo, useState } from "react"
import { Check, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { settingsApi, type EditableSetting } from "@/features/system/settingsApi"
import { AdminOverlay } from "./AdminOverlay"

const BOOL_TRUE = new Set(["1", "true", "yes", "on"])

type RowStatus = "idle" | "saving" | "saved" | "error"

function SettingRow({ s, onSaved }: { s: EditableSetting; onSaved: (u: EditableSetting) => void }) {
  const [draft, setDraft] = useState(s.type === "secret" ? "" : s.value)
  const [status, setStatus] = useState<RowStatus>("idle")

  async function save(value: string) {
    setStatus("saving")
    try {
      onSaved(await settingsApi.update(s.key, value))
      setStatus("saved")
      setTimeout(() => setStatus("idle"), 1500)
    } catch { setStatus("error") }
  }

  const boolOn = BOOL_TRUE.has(s.value.toLowerCase())

  return (
    <div className="flex items-start gap-3 border-b border-[#2a364b] py-2.5 last:border-0">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm text-[#e8eef8]">{s.label}</span>
          {s.overridden && (
            <span className="rounded border border-violet-500/25 bg-violet-500/15 px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-violet-300">GUI</span>
          )}
          {status === "saved" && <Check size={13} className="text-emerald-400" />}
          {status === "saving" && <Loader2 size={13} className="animate-spin text-[#8d9ab0]" />}
          {status === "error" && <span className="text-[11px] text-rose-400">Fehler</span>}
        </div>
        {s.help && <p className="mt-0.5 text-xs leading-snug text-[#8d9ab0]">{s.help}</p>}
      </div>

      <div className="w-56 shrink-0">
        {s.type === "bool" ? (
          <button type="button" onClick={() => save(boolOn ? "0" : "1")} aria-pressed={boolOn}
            className={`relative h-6 w-11 rounded-full transition-colors ${boolOn ? "bg-emerald-500/70" : "bg-[#2a364b]"}`}>
            <span className={`absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${boolOn ? "translate-x-5" : ""}`} />
          </button>
        ) : (
          <input
            type={s.type === "secret" ? "password" : s.type === "int" ? "number" : "text"}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={() => { const original = s.type === "secret" ? "" : s.value; if (draft !== original) save(draft) }}
            placeholder={s.type === "secret" && s.is_set ? "•••••••• (gesetzt)" : ""}
            className="w-full rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-1.5 text-sm text-[#e8eef8] transition-colors placeholder:text-[#5b6675] focus:border-violet-500/50 focus:outline-none"
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
      .then((r) => setSettings(r.settings))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Fehler"))
  }, [])

  const groups = useMemo(() => {
    const m = new Map<string, EditableSetting[]>()
    for (const s of settings ?? []) {
      const arr = m.get(s.group) ?? []
      arr.push(s)
      m.set(s.group, arr)
    }
    return Array.from(m.entries())
  }, [settings])

  function onSaved(updated: EditableSetting) {
    setSettings((prev) => prev?.map((s) => (s.key === updated.key ? updated : s)) ?? prev)
  }

  return (
    <AdminOverlay eyebrow="Admin" title={t("settings.title")} onClose={onClose} maxWidthClass="max-w-3xl">
      <div className="space-y-4">
        <p className="text-sm text-[#8d9ab0]">{t("settings.subtitle")}</p>

        {error && <p className="text-sm text-rose-300">{error}</p>}
        {!settings && !error && <Loader2 size={18} className="animate-spin text-[#8d9ab0]" />}

        {groups.map(([group, rows]) => (
          <div key={group} className="overflow-hidden rounded-[6px] border border-[#2a364b] bg-[#111827]">
            <div className="border-b border-[#2a364b] bg-[#131b2a] px-4 py-2 text-xs font-semibold uppercase tracking-wider text-[#8d9ab0]">{group}</div>
            <div className="px-4 py-1">
              {rows.map((s) => <SettingRow key={s.key} s={s} onSaved={onSaved} />)}
            </div>
          </div>
        ))}
      </div>
    </AdminOverlay>
  )
}
