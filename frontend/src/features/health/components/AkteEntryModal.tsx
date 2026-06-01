import { useTranslation } from "react-i18next"
import { useState } from "react"
import { akteApi, type AkteEntityKey, type AkteRecord, type AkteUiField } from "../api"

interface Props {
  entity: AkteEntityKey
  title: string
  fields: AkteUiField[]
  /** vorhandener Eintrag → Bearbeiten; undefined → Neu anlegen */
  existing?: AkteRecord
  onClose: () => void
  onSaved: () => void
}

function initialForm(fields: AkteUiField[], existing?: AkteRecord): Record<string, string> {
  const f: Record<string, string> = {}
  for (const fd of fields) {
    const v = existing?.record?.[fd.key]
    f[fd.key] = v === null || v === undefined ? "" : String(v)
  }
  return f
}

export function AkteEntryModal({ entity, title, fields, existing, onClose, onSaved }: Props) {
  const { t } = useTranslation("health")
  const [form, setForm] = useState<Record<string, string>>(() => initialForm(fields, existing))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Nur ausgefüllte Felder senden; number-Felder casten.
    const payload: Record<string, unknown> = {}
    for (const fd of fields) {
      const raw = form[fd.key]?.trim()
      if (!raw) continue
      payload[fd.key] = fd.type === "number" ? Number(raw) : raw
    }

    const required = fields.find((fd) => fd.required)
    if (required && !payload[required.key]) {
      setError(`${required.label} ist erforderlich.`)
      return
    }

    setSaving(true)
    try {
      if (existing) {
        await akteApi.updateEntity(entity, existing.id, payload)
      } else {
        await akteApi.createEntity(entity, payload)
      }
      onSaved()
      onClose()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg max-h-[85vh] overflow-y-auto rounded-2xl border border-white/[8%] bg-zinc-900 p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-zinc-100">
            {existing ? t("akte.edit") : t("akte.new")}: {title}
          </h2>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-300 text-xl leading-none"
            aria-label={t("akte.close")}
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <div className="grid grid-cols-2 gap-3">
            {fields.map((fd) => (
              <label
                key={fd.key}
                className={`flex flex-col gap-1 text-xs text-zinc-400 ${fd.type === "textarea" ? "col-span-2" : ""}`}
              >
                {fd.label}{fd.required && <span className="text-rose-400"> *</span>}
                {fd.type === "textarea" ? (
                  <textarea
                    value={form[fd.key] ?? ""}
                    onChange={(e) => set(fd.key, e.target.value)}
                    rows={3}
                    className="rounded-lg border border-white/[8%] bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600"
                  />
                ) : fd.type === "select" ? (
                  <select
                    value={form[fd.key] ?? ""}
                    onChange={(e) => set(fd.key, e.target.value)}
                    className="rounded-lg border border-white/[8%] bg-zinc-800 px-3 py-2 text-sm text-zinc-100"
                  >
                    <option value="">—</option>
                    {fd.options.map((o) => <option key={o} value={o}>{o}</option>)}
                  </select>
                ) : (
                  <input
                    type={fd.type === "number" ? "number" : fd.type === "date" ? "date" : "text"}
                    step={fd.type === "number" ? "any" : undefined}
                    value={form[fd.key] ?? ""}
                    onChange={(e) => set(fd.key, e.target.value)}
                    placeholder={fd.placeholder ?? undefined}
                    className="rounded-lg border border-white/[8%] bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600"
                  />
                )}
              </label>
            ))}
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 rounded-lg border border-white/[6%] hover:bg-white/[4%] transition-colors"
            >
              Abbrechen
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-rose-500/20 border border-rose-500/30 text-rose-300 hover:bg-rose-500/30 transition-colors disabled:opacity-50"
            >
              {saving ? t("akte.saving") : t("akte.save")}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
