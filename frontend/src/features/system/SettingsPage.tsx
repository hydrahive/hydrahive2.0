import { useEffect, useMemo, useState, type CSSProperties } from "react"
import { Check, Loader2, Settings as SettingsIcon } from "lucide-react"
import { useTranslation } from "react-i18next"
import { settingsApi, type EditableSetting } from "./settingsApi"
import { rgbFor } from "@/shared/colors"

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
    } catch {
      setStatus("error")
    }
  }

  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-white/[5%] last:border-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm text-zinc-200">{s.label}</span>
          {s.overridden && (
            <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-violet-500/15 text-violet-300 border border-violet-500/25">GUI</span>
          )}
          {status === "saved" && <Check size={13} className="text-emerald-400" />}
          {status === "saving" && <Loader2 size={13} className="text-zinc-500 animate-spin" />}
          {status === "error" && <span className="text-[11px] text-rose-400">Fehler</span>}
        </div>
        {s.help && <p className="text-xs text-zinc-500 mt-0.5 leading-snug">{s.help}</p>}
      </div>

      <div className="shrink-0 w-56">
        {s.type === "bool" ? (
          <button
            type="button"
            onClick={() => save(BOOL_TRUE.has(s.value.toLowerCase()) ? "0" : "1")}
            className={`relative w-11 h-6 rounded-full transition-colors ${
              BOOL_TRUE.has(s.value.toLowerCase()) ? "bg-emerald-500/70" : "bg-zinc-700"
            }`}
            aria-pressed={BOOL_TRUE.has(s.value.toLowerCase())}
          >
            <span className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
              BOOL_TRUE.has(s.value.toLowerCase()) ? "translate-x-5" : ""
            }`} />
          </button>
        ) : (
          <input
            type={s.type === "secret" ? "password" : s.type === "int" ? "number" : "text"}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={() => {
              const original = s.type === "secret" ? "" : s.value
              if (draft !== original) save(draft)
            }}
            placeholder={s.type === "secret" && s.is_set ? "•••••••• (gesetzt)" : ""}
            className="w-full px-3 py-1.5 rounded-lg bg-white/[4%] border border-white/[8%] text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-violet-500/50 transition-colors"
          />
        )}
      </div>
    </div>
  )
}

export function SettingsPage() {
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
    <div className="max-w-3xl mx-auto space-y-4">
      <div className="flex items-center gap-2.5">
        <SettingsIcon size={20} className="text-violet-300" />
        <h1 className="text-xl font-bold text-white">{t("settings.title")}</h1>
      </div>
      <p className="text-sm text-zinc-500">{t("settings.subtitle")}</p>

      {error && <p className="text-sm text-rose-300">{error}</p>}
      {!settings && !error && <Loader2 size={18} className="text-zinc-500 animate-spin" />}

      {groups.map(([group, rows]) => (
        <div key={group} className="box overflow-hidden" style={{ "--c": rgbFor("/system") } as CSSProperties}>
          <div className="box-h"><span className="t">{group}</span></div>
          <div className="box-b py-1">
            {rows.map((s) => <SettingRow key={s.key} s={s} onSaved={onSaved} />)}
          </div>
        </div>
      ))}
    </div>
  )
}
