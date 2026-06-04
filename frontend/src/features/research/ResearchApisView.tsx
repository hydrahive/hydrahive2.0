import { useEffect, useState, type CSSProperties } from "react"
import {
  researchApi,
  type ResearchApiPublic,
  type ResearchCategory,
  type ResearchTestResult,
} from "./api"
import { rgbFor } from "@/shared/colors"

const CATEGORY_LABELS: Record<ResearchCategory, string> = {
  literatur: "📚 Literatur & Studien",
  medikamente: "💊 Medikamente & Wirkstoffe",
  krankheiten_gene: "🧬 Krankheiten, Gene, Diagnosen",
  studien: "🔬 Klinische Studien",
}
const CATEGORY_ORDER: ResearchCategory[] = ["literatur", "medikamente", "krankheiten_gene", "studien"]

function ApiCard({ api, onChange }: { api: ResearchApiPublic; onChange: (a: ResearchApiPublic) => void }) {
  const [keyInput, setKeyInput] = useState("")
  const [busy, setBusy] = useState(false)
  const [test, setTest] = useState<ResearchTestResult | null>(null)

  async function toggle() {
    setBusy(true)
    try {
      onChange(await researchApi.update(api.id, { enabled: !api.enabled }))
    } finally {
      setBusy(false)
    }
  }

  async function saveKey() {
    if (!keyInput.trim()) return
    setBusy(true)
    try {
      onChange(await researchApi.update(api.id, { key: keyInput.trim() }))
      setKeyInput("")
    } finally {
      setBusy(false)
    }
  }

  async function runTest() {
    setBusy(true)
    setTest(null)
    try {
      setTest(await researchApi.test(api.id))
    } finally {
      setBusy(false)
    }
  }

  const showKeyField = api.auth_type !== "none"

  return (
    <div className="box overflow-hidden p-4 flex flex-col gap-2" style={{ "--c": rgbFor("/health") } as CSSProperties}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-zinc-100">{api.name}</span>
            {api.needs_key && !api.has_key && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300">Key nötig</span>
            )}
            {api.has_key && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300">Key gesetzt</span>
            )}
          </div>
          <p className="text-xs text-zinc-500 mt-0.5">{api.description}</p>
          {api.rate_limit && <p className="text-[10px] text-zinc-600 mt-0.5">{api.rate_limit}</p>}
        </div>
        <label className="flex items-center gap-2 shrink-0 cursor-pointer">
          <input
            type="checkbox"
            checked={api.enabled}
            disabled={busy}
            onChange={toggle}
            className="accent-rose-500"
          />
          <span className="text-xs text-zinc-400">{api.enabled ? "aktiv" : "aus"}</span>
        </label>
      </div>

      {showKeyField && (
        <div className="flex items-center gap-2">
          <input
            type="password"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            placeholder={
              api.has_key
                ? "•••• gesetzt — neu eingeben zum Ersetzen"
                : `${api.auth_type === "bearer" ? "Token" : "API-Key"} eingeben`
            }
            className="flex-1 text-xs bg-black/30 border border-white/10 rounded px-2 py-1 text-zinc-200"
          />
          <button
            onClick={saveKey}
            disabled={busy || !keyInput.trim()}
            className="text-xs px-2 py-1 rounded bg-rose-500/15 text-rose-300 disabled:opacity-40"
          >
            Speichern
          </button>
        </div>
      )}

      <div className="flex items-center gap-3 text-[11px]">
        {api.docs_url && (
          <a href={api.docs_url} target="_blank" rel="noreferrer" className="text-sky-400 hover:underline">
            Docs ↗
          </a>
        )}
        <button onClick={runTest} disabled={busy} className="text-zinc-400 hover:text-zinc-200">
          Test
        </button>
        {test && (
          <span className={test.ok ? "text-emerald-400" : "text-rose-400"}>
            {test.ok ? `OK (${test.status})` : `Fehler: ${test.error ?? test.status}`}
          </span>
        )}
      </div>
    </div>
  )
}

export function ResearchApisView() {
  const [apis, setApis] = useState<ResearchApiPublic[] | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    researchApi
      .list()
      .then((r) => setApis(r.apis))
      .catch(() => setError(true))
  }, [])

  function patch(updated: ResearchApiPublic) {
    setApis((prev) => prev?.map((a) => (a.id === updated.id ? updated : a)) ?? null)
  }

  if (error) return <p className="text-sm text-rose-400">Forschungs-APIs sind nur für Admins konfigurierbar.</p>
  if (apis === null) return <div className="h-48 rounded-xl bg-zinc-900/50 animate-pulse" />

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-base font-semibold text-zinc-100">Forschungs-APIs</h2>
        <p className="text-xs text-zinc-500">
          Wissenschaftliche &amp; medizinische Quellen für die Agenten. Keyless-Quellen sind aktiv;
          Key/Token nur wo nötig.
        </p>
      </div>
      {CATEGORY_ORDER.map((cat) => {
        const inCat = apis.filter((a) => a.category === cat)
        if (inCat.length === 0) return null
        return (
          <div key={cat}>
            <p className="text-[11px] font-bold uppercase tracking-widest text-zinc-600 mb-2">
              {CATEGORY_LABELS[cat]}
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              {inCat.map((a) => (
                <ApiCard key={a.id} api={a} onChange={patch} />
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
