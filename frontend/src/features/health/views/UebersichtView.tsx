import { useTranslation } from "react-i18next"
import { useEffect, useState } from "react"
import { egaApi } from "../api"
import { EgaImportButton } from "../components/EgaImportButton"

const CATEGORIES = [
  { type: "Encounter",           icon: "🏥", label: "Arztbesuche" },
  { type: "AmbulantClaim",       icon: "🧾", label: "Abrechnungen" },
  { type: "MedicationDispense",  icon: "💊", label: "Medikamente" },
  { type: "HospitalStay",        icon: "🛏", label: "Krankenhaus" },
  { type: "Procedure",           icon: "🔬", label: "Vorsorge" },
  { type: "Condition",           icon: "📋", label: "Diagnosen" },
]

interface Costs {
  ambulant_eur: number
  medikamente_eur: number
  medikamente_zuzahlung_eur: number
}

function fmt(n: number) {
  return n.toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €"
}

export function UebersichtView() {
  const { t } = useTranslation("health")
  const [summary, setSummary] = useState<Record<string, number> | null>(null)
  const [costs, setCosts] = useState<Costs | null>(null)

  const load = () => {
    egaApi.getSummary().then(setSummary).catch(() => setSummary({}))
    egaApi.getCosts().then(setCosts).catch(() => {})
  }

  useEffect(() => { load() }, [])

  const hasCosts = costs && (costs.ambulant_eur > 0 || costs.medikamente_eur > 0)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-zinc-100">Übersicht</h2>
        <EgaImportButton onImported={load} />
      </div>

      {summary === null ? (
        <div className="grid grid-cols-3 gap-3">
          {CATEGORIES.map((c) => (
            <div key={c.type} className="h-20 rounded-xl bg-zinc-900/50 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-3">
          {CATEGORIES.map((c) => (
            <div key={c.type} className="rounded-xl border border-white/[6%] bg-zinc-900/40 p-4">
              <div className="text-lg mb-1">{c.icon}</div>
              <div className="text-2xl font-bold text-zinc-100">{summary[c.type] ?? 0}</div>
              <div className="text-xs text-zinc-500 mt-0.5">{c.label}</div>
            </div>
          ))}
        </div>
      )}

      {hasCosts && (
        <div>
          <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-600 mb-2">Kosten (Kassenleistungen)</h3>
          <div className="rounded-xl border border-white/[6%] bg-zinc-900/40 divide-y divide-white/[4%]">
            <div className="flex items-center justify-between px-4 py-2.5">
              <span className="text-sm text-zinc-400">Arztbesuche abgerechnet</span>
              <span className="text-sm font-medium text-zinc-200">{fmt(costs!.ambulant_eur)}</span>
            </div>
            <div className="flex items-center justify-between px-4 py-2.5">
              <span className="text-sm text-zinc-400">Apothekenpreise gesamt</span>
              <span className="text-sm font-medium text-zinc-200">{fmt(costs!.medikamente_eur)}</span>
            </div>
            {costs!.medikamente_zuzahlung_eur > 0 && (
              <div className="flex items-center justify-between px-4 py-2.5">
                <span className="text-sm text-zinc-400">Davon deine Zuzahlung</span>
                <span className="text-sm font-medium text-rose-400">{fmt(costs!.medikamente_zuzahlung_eur)}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {summary && Object.keys(summary).length === 0 && (
        <div className="rounded-xl border border-dashed border-white/10 p-8 text-center">
          <p className="text-zinc-500 text-sm">{t("empty")}</p>
          <p className="text-zinc-600 text-xs mt-1">TK-Safe App öffnen → Akte exportieren → ZIP hier hochladen.</p>
        </div>
      )}
    </div>
  )
}
