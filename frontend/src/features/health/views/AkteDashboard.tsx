import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { akteApi, type AktePatient } from "../api"
import { useAkteSchema } from "../useAkteSchema"

function calcAge(geb: string): number {
  const birth = new Date(geb)
  const today = new Date()
  let age = today.getFullYear() - birth.getFullYear()
  const m = today.getMonth() - birth.getMonth()
  if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--
  return age
}

interface Props {
  /** called after akte is successfully created/updated */
  onSaved?: () => void
}

export function AkteDashboard({ onSaved }: Props) {
  const navigate = useNavigate()
  const schema = useAkteSchema()
  const [akte, setAkte] = useState<AktePatient | null | "loading">("loading")
  const [summary, setSummary] = useState<Record<string, number> | null>(null)
  const [conditions, setConditions] = useState<unknown[]>([])
  const [allergies, setAllergies] = useState<unknown[]>([])
  const [medications, setMedications] = useState<unknown[]>([])

  // Form state
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ name: "", vorname: "", geburtsdatum: "", geschlecht: "m" })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    setAkte("loading")
    akteApi.getOwn()
      .then((a) => {
        setAkte(a)
        setForm({
          name: a.name ?? "",
          vorname: a.vorname ?? "",
          geburtsdatum: a.geburtsdatum ?? "",
          geschlecht: a.geschlecht ?? "m",
        })
        return akteApi.getSummary()
      })
      .then(setSummary)
      .catch((e: Error & { status?: number }) => {
        if (e.status === 404 || e.message.includes("404") || e.message.includes("Keine Akte")) {
          setAkte(null)
        } else {
          setError(e.message)
        }
      })
  }

  useEffect(() => { load() }, [])

  // Load critical entity data when akte exists
  useEffect(() => {
    if (!akte || akte === "loading" || akte === null || !schema) return
    const lf = (e: "conditions" | "allergies" | "medications") => schema.entities[e].label_fields
    akteApi.listEntity("conditions", { status: "aktuell" }, lf("conditions")).then(setConditions).catch(() => {})
    akteApi.listEntity("allergies", undefined, lf("allergies")).then(setAllergies).catch(() => {})
    akteApi.listEntity("medications", { status: "aktuell" }, lf("medications")).then(setMedications).catch(() => {})
  }, [akte, schema])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await akteApi.createOwn(form)
      await load()
      setEditing(false)
      onSaved?.()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await akteApi.updateOwn(form)
      await load()
      setEditing(false)
      onSaved?.()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  // ── No akte yet ──────────────────────────────────────────────────────────
  if (akte === null) {
    return (
      <div className="space-y-6">
        <div className="rounded-xl border border-white/[6%] bg-zinc-900/40 p-8 text-center space-y-4">
          <div className="text-4xl">🗂</div>
          <div>
            <h2 className="text-lg font-semibold text-zinc-100 mb-1">Meine Patientenakte</h2>
            <p className="text-sm text-zinc-500">Lege jetzt deine eigene Akte an — alles an einem Ort, privat und sicher.</p>
          </div>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <form onSubmit={handleCreate} className="max-w-sm mx-auto space-y-3 text-left">
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1 text-xs text-zinc-400">
                Vorname
                <input
                  required
                  value={form.vorname}
                  onChange={(e) => setForm((f) => ({ ...f, vorname: e.target.value }))}
                  className="rounded-lg border border-white/[8%] bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600"
                  placeholder="Max"
                />
              </label>
              <label className="flex flex-col gap-1 text-xs text-zinc-400">
                Nachname
                <input
                  required
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  className="rounded-lg border border-white/[8%] bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600"
                  placeholder="Mustermann"
                />
              </label>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1 text-xs text-zinc-400">
                Geburtsdatum
                <input
                  required
                  type="date"
                  value={form.geburtsdatum}
                  onChange={(e) => setForm((f) => ({ ...f, geburtsdatum: e.target.value }))}
                  className="rounded-lg border border-white/[8%] bg-zinc-800 px-3 py-2 text-sm text-zinc-100"
                />
              </label>
              <label className="flex flex-col gap-1 text-xs text-zinc-400">
                Geschlecht
                <select
                  value={form.geschlecht}
                  onChange={(e) => setForm((f) => ({ ...f, geschlecht: e.target.value }))}
                  className="rounded-lg border border-white/[8%] bg-zinc-800 px-3 py-2 text-sm text-zinc-100"
                >
                  <option value="m">Männlich</option>
                  <option value="w">Weiblich</option>
                  <option value="d">Divers</option>
                </select>
              </label>
            </div>
            <button
              type="submit"
              disabled={saving}
              className="w-full rounded-lg bg-rose-500/20 border border-rose-500/30 text-rose-300 py-2 text-sm font-medium hover:bg-rose-500/30 transition-colors disabled:opacity-50"
            >
              {saving ? "Wird angelegt…" : "Akte anlegen"}
            </button>
          </form>
        </div>
      </div>
    )
  }

  // ── Loading ─────────────────────────────────────────────────────────────
  if (akte === "loading") {
    return (
      <div className="space-y-4">
        <div className="h-24 rounded-xl bg-zinc-900/50 animate-pulse" />
        <div className="grid grid-cols-3 gap-3">
          {[1, 2, 3].map((i) => <div key={i} className="h-20 rounded-xl bg-zinc-900/50 animate-pulse" />)}
        </div>
      </div>
    )
  }

  // ── Akte exists ──────────────────────────────────────────────────────────
  const age = calcAge(akte.geburtsdatum)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-xl border border-white/[6%] bg-zinc-900/40 p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-2xl">
              {akte.vorname?.[0]}{akte.name?.[0]}
            </div>
            <div>
              <h2 className="text-xl font-bold text-zinc-100">
                {akte.vorname} {akte.name}
              </h2>
              <p className="text-sm text-zinc-500">
                {new Date(akte.geburtsdatum).toLocaleDateString("de-DE")}
                {" · "}{age} Jahre
                {" · "}{akte.geschlecht === "m" ? "♂ Männlich" : akte.geschlecht === "w" ? "♀ Weiblich" : "⚥ Divers"}
              </p>
            </div>
          </div>
          <button
            onClick={() => setEditing((e) => !e)}
            className="text-xs text-zinc-500 hover:text-zinc-300 px-3 py-1.5 rounded-lg border border-white/[6%] hover:bg-white/[4%] transition-colors"
          >
            {editing ? "Abbrechen" : "Bearbeiten"}
          </button>
        </div>

        {editing && (
          <form onSubmit={handleUpdate} className="mt-4 pt-4 border-t border-white/[6%] space-y-3">
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1 text-xs text-zinc-400">
                Vorname
                <input
                  required
                  value={form.vorname}
                  onChange={(e) => setForm((f) => ({ ...f, vorname: e.target.value }))}
                  className="rounded-lg border border-white/[8%] bg-zinc-800 px-3 py-2 text-sm text-zinc-100"
                />
              </label>
              <label className="flex flex-col gap-1 text-xs text-zinc-400">
                Nachname
                <input
                  required
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  className="rounded-lg border border-white/[8%] bg-zinc-800 px-3 py-2 text-sm text-zinc-100"
                />
              </label>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1 text-xs text-zinc-400">
                Geburtsdatum
                <input
                  required
                  type="date"
                  value={form.geburtsdatum}
                  onChange={(e) => setForm((f) => ({ ...f, geburtsdatum: e.target.value }))}
                  className="rounded-lg border border-white/[8%] bg-zinc-800 px-3 py-2 text-sm text-zinc-100"
                />
              </label>
              <label className="flex flex-col gap-1 text-xs text-zinc-400">
                Geschlecht
                <select
                  value={form.geschlecht}
                  onChange={(e) => setForm((f) => ({ ...f, geschlecht: e.target.value }))}
                  className="rounded-lg border border-white/[8%] bg-zinc-800 px-3 py-2 text-sm text-zinc-100"
                >
                  <option value="m">Männlich</option>
                  <option value="w">Weiblich</option>
                  <option value="d">Divers</option>
                </select>
              </label>
            </div>
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-rose-500/20 border border-rose-500/30 text-rose-300 px-4 py-2 text-sm font-medium hover:bg-rose-500/30 transition-colors disabled:opacity-50"
            >
              {saving ? "Speichern…" : "Speichern"}
            </button>
          </form>
        )}
      </div>

      {/* Count Kacheln */}
      {summary && (
        <div className="grid grid-cols-3 gap-3">
          {(["conditions", "medications", "observations", "allergies", "events", "imaging", "practitioners", "documents", "notes"] as const).map((key) => (
            <div
              key={key}
              onClick={() => navigate(`/health/${key}`)}
              className="rounded-xl border border-white/[6%] bg-zinc-900/40 p-4 cursor-pointer hover:bg-white/[2%] transition-colors"
            >
              <div className="text-2xl font-bold text-zinc-100">{summary[key] ?? 0}</div>
              <div className="text-xs text-zinc-500 mt-0.5 capitalize">
                {key === "practitioners" ? "Ärzte" : key}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Rote Fakten */}
      <div className="space-y-3">
        {/* Aktive Diagnosen */}
        {conditions.length > 0 && (
          <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4">
            <h3 className="text-sm font-semibold text-red-300 mb-2">🔴 Aktive Diagnosen</h3>
            <ul className="space-y-1">
              {conditions.slice(0, 5).map((c: any) => (
                <li key={c.id} className="text-sm text-zinc-300">
                  <span className="text-zinc-500 mr-2">●</span>
                  {c.label}
                  {c.record?.icd_code && <span className="ml-2 text-zinc-600 text-xs">{c.record.icd_code}</span>}
                </li>
              ))}
              {conditions.length > 5 && (
                <li className="text-xs text-zinc-600">+{conditions.length - 5} weitere</li>
              )}
            </ul>
          </div>
        )}

        {/* Allergien */}
        {allergies.length > 0 && (
          <div className="rounded-xl border border-orange-500/20 bg-orange-500/5 p-4">
            <h3 className="text-sm font-semibold text-orange-300 mb-2">⚠️ Allergien</h3>
            <ul className="space-y-1">
              {allergies.slice(0, 5).map((a: any) => (
                <li key={a.id} className="text-sm text-zinc-300">
                  <span className="text-orange-400 mr-2">●</span>
                  {a.label}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Dauermedikation */}
        {medications.length > 0 && (
          <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4">
            <h3 className="text-sm font-semibold text-blue-300 mb-2">💊 Dauermedikation</h3>
            <ul className="space-y-1">
              {medications.slice(0, 5).map((m: any) => (
                <li key={m.id} className="text-sm text-zinc-300">
                  <span className="text-blue-400 mr-2">●</span>
                  {m.label}
                  {m.record?.dosierung && <span className="ml-2 text-zinc-500 text-xs">— {m.record.dosierung}</span>}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}
    </div>
  )
}