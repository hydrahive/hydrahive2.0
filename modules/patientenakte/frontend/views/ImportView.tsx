import { useEffect, useState, type CSSProperties } from "react"
import { useTranslation } from "react-i18next"
import { egaApi, fhirApi, type EgaRecord, type EgaTimelineEntry } from "../api"
import { ImportButton } from "../components/ImportButton"
import { rgbFor } from "@/shared/colors"

const C = { "--c": rgbFor("/akte") } as CSSProperties

// eGA dto_type → Icon (Label kommt aus i18n import.types.<type>)
const TYPE_ICONS: Record<string, string> = {
  Encounter: "🏥",
  AmbulantClaim: "🧾",
  MedicationDispense: "💊",
  MedicationClaim: "🧾",
  HospitalStay: "🛏",
  Procedure: "🔬",
  Condition: "📋",
}

interface Costs {
  ambulant_eur: number
  medikamente_eur: number
  medikamente_zuzahlung_eur: number
}

function eur(n: number): string {
  return n.toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €"
}

export function ImportView() {
  const { t } = useTranslation("akte")
  const [summary, setSummary] = useState<Record<string, number> | null>(null)
  const [costs, setCosts] = useState<Costs | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [records, setRecords] = useState<EgaRecord[] | null>(null)
  const [timeline, setTimeline] = useState<EgaTimelineEntry[] | null>(null)

  const loadOverview = () => {
    egaApi.getSummary().then(setSummary).catch(() => setSummary({}))
    egaApi.getCosts().then(setCosts).catch(() => setCosts(null))
    egaApi.getTimeline().then((d) => setTimeline(d.entries)).catch(() => setTimeline([]))
  }

  useEffect(() => { loadOverview() }, [])

  const loadRecords = (type: string) => {
    setRecords(null)
    egaApi.getRecords(type).then((d) => setRecords(d.records)).catch(() => setRecords([]))
  }

  useEffect(() => {
    if (!selected) { setRecords(null); return }
    loadRecords(selected)
  }, [selected])

  const onImported = () => { loadOverview(); if (selected) loadRecords(selected) }

  const typeLabel = (type: string) => t(`import.types.${type}`, { defaultValue: type })
  const fmtDate = (d: string | null) => (d ? new Date(d).toLocaleDateString("de-DE") : "")

  const hasCosts = costs && (costs.ambulant_eur > 0 || costs.medikamente_eur > 0)
  const isEmpty = summary && Object.keys(summary).length === 0
  const types = summary ? Object.keys(summary).sort((a, b) => (summary[b] - summary[a])) : []

  return (
    <div className="space-y-6">
      {/* Header + Import */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="text-base font-semibold text-zinc-100">{t("import.title")}</h2>
        <div className="flex items-center gap-2 flex-wrap">
          <ImportButton
            label={t("import.ega_button")}
            accept=".zip"
            onImport={(f) => egaApi.importZip(f)}
            onDone={onImported}
          />
          <ImportButton
            label={t("import.fhir_button")}
            accept=".json,.zip"
            onImport={(f) => (f.name.endsWith(".zip") ? fhirApi.importEgaZip(f) : fhirApi.importBundle(f))}
            onDone={onImported}
          />
        </div>
      </div>

      <p className="text-xs text-zinc-500">{t("import.subtitle")}</p>

      {/* Empty state */}
      {isEmpty && (
        <div className="box overflow-hidden p-8 text-center" style={C}>
          <p className="text-zinc-500 text-sm">{t("import.empty")}</p>
          <p className="text-zinc-600 text-xs mt-1">{t("import.empty_hint")}</p>
        </div>
      )}

      {/* Summary-Kacheln */}
      {summary === null ? (
        <div className="grid grid-cols-3 gap-3">
          {[0, 1, 2].map((i) => <div key={i} className="h-20 rounded-xl bg-zinc-900/50 animate-pulse" />)}
        </div>
      ) : !isEmpty && (
        <div className="grid grid-cols-3 gap-3">
          {types.map((type) => (
            <button
              key={type}
              onClick={() => setSelected((s) => (s === type ? null : type))}
              className={`box overflow-hidden p-4 text-left transition-colors ${
                selected === type ? "ring-1 ring-rose-500/40" : "hover:bg-white/[2%]"
              }`}
              style={C}
            >
              <div className="text-lg mb-1">{TYPE_ICONS[type] ?? "📄"}</div>
              <div className="text-2xl font-bold text-zinc-100">{summary[type]}</div>
              <div className="text-xs text-zinc-500 mt-0.5">{typeLabel(type)}</div>
            </button>
          ))}
        </div>
      )}

      {/* Kosten */}
      {hasCosts && (
        <div>
          <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-600 mb-2">{t("import.costs_title")}</h3>
          <div className="box overflow-hidden divide-y divide-white/[4%]" style={C}>
            <div className="flex items-center justify-between px-4 py-2.5">
              <span className="text-sm text-zinc-400">{t("import.cost_ambulant")}</span>
              <span className="text-sm font-medium text-zinc-200">{eur(costs!.ambulant_eur)}</span>
            </div>
            <div className="flex items-center justify-between px-4 py-2.5">
              <span className="text-sm text-zinc-400">{t("import.cost_medication")}</span>
              <span className="text-sm font-medium text-zinc-200">{eur(costs!.medikamente_eur)}</span>
            </div>
            {costs!.medikamente_zuzahlung_eur > 0 && (
              <div className="flex items-center justify-between px-4 py-2.5">
                <span className="text-sm text-zinc-400">{t("import.cost_copay")}</span>
                <span className="text-sm font-medium text-rose-400">{eur(costs!.medikamente_zuzahlung_eur)}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Records: gewählter Typ → Liste; sonst Zeitstrahl */}
      {!isEmpty && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-600">
              {selected ? typeLabel(selected) : t("import.timeline_title")}
            </h3>
            {selected && (
              <button onClick={() => setSelected(null)} className="text-xs text-zinc-500 hover:text-zinc-300">
                ← {t("import.all")}
              </button>
            )}
          </div>

          {selected ? (
            records === null ? (
              <div className="h-32 rounded-xl bg-zinc-900/50 animate-pulse" />
            ) : records.length === 0 ? (
              <p className="text-sm text-zinc-500 py-6 text-center">{t("import.records_empty")}</p>
            ) : (
              <div className="box overflow-hidden" style={C}>
                {records.map((r) => (
                  <div key={r.id} className="flex items-center justify-between gap-3 px-4 py-2.5 border-b border-white/[4%] last:border-0 hover:bg-white/[2%]">
                    <span className="text-sm text-zinc-200 truncate">{r.display}</span>
                    <span className="text-xs text-zinc-500 shrink-0">{fmtDate(r.sort_date)}</span>
                  </div>
                ))}
              </div>
            )
          ) : (
            timeline === null ? (
              <div className="h-32 rounded-xl bg-zinc-900/50 animate-pulse" />
            ) : (
              <div className="box overflow-hidden" style={C}>
                {timeline.slice(0, 100).map((e) => (
                  <div key={e.id} className="flex items-center justify-between gap-3 px-4 py-2.5 border-b border-white/[4%] last:border-0 hover:bg-white/[2%]">
                    <div className="min-w-0 flex items-center gap-2">
                      <span className="text-xs">{TYPE_ICONS[e.dto_type] ?? "📄"}</span>
                      <span className="text-sm text-zinc-200 truncate">{e.display}</span>
                    </div>
                    <span className="text-xs text-zinc-500 shrink-0">{fmtDate(e.sort_date)}</span>
                  </div>
                ))}
              </div>
            )
          )}
        </div>
      )}
    </div>
  )
}
