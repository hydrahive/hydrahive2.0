import { useEffect, useState } from "react"
import { Navigate, Route, Routes } from "react-router-dom"
import { Activity } from "lucide-react"
import { HealthSidebar } from "./HealthSidebar"
import { KiFloatingButton } from "./KiFloatingButton"
import { AkteDashboard }  from "./views/AkteDashboard"
import { AkteTimeline }  from "./views/AkteTimeline"
import { AkteEntityList } from "./views/AkteEntityList"
import { AkteLabCharts } from "./views/AkteLabCharts"
import { healthApi, type MetricsSummary } from "./api"

function AppleHealthView() {
  const [summary, setSummary] = useState<MetricsSummary | null>(null)

  useEffect(() => {
    healthApi.metrics(30).then(setSummary).catch(() => {
      setSummary({ metrics: {}, last_ingest: null, period_days: 30 })
    })
  }, [])

  if (summary === null) {
    return <div className="h-48 rounded-xl bg-zinc-900/50 animate-pulse" />
  }

  return (
    <div className="space-y-4">
      <div className="text-sm text-zinc-500">
        Apple Health Daten werden automatisch synchronisiert.
      </div>
      {/* Placeholder — AkteDashboard replaces UebersichtView as primary */}
    </div>
  )
}

function ImportView() {
  return (
    <div className="space-y-6">
      <h2 className="text-base font-semibold text-zinc-100">📥 eGA / FHIR Import</h2>
      <p className="text-sm text-zinc-500">
        Importiere Daten aus der elektronischen Gesundheitsakte (eGA) der Techniker Krankenkasse
        oder aus beliebigen FHIR-Bundles. Importierte Daten sind read-only und bleiben
        vom eigenen Akten-Bereich getrennt.
      </p>
      <div className="rounded-xl border border-white/[6%] bg-zinc-900/40 p-6 text-center text-sm text-zinc-500">
        Import-Funktionen werden in Kürze verfügbar sein.
      </div>
    </div>
  )
}

export function HealthPage() {
  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-9 h-9 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
          <Activity size={18} className="text-rose-400" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-zinc-100">Gesundheit</h1>
          <p className="text-xs text-zinc-500">Meine Patientenakte</p>
        </div>
      </div>

      <div className="flex gap-6">
        <HealthSidebar />
        <div className="flex-1 min-w-0 relative">
          <Routes>
            {/* Meine Akte */}
            <Route index element={<Navigate to="uebersicht" replace />} />
            <Route path="uebersicht"     element={<AkteDashboard />} />
            <Route path="timeline"       element={<AkteTimeline />} />
            <Route path="conditions"    element={<AkteEntityList entity="conditions" />} />
            <Route path="medications"   element={<AkteEntityList entity="medications" />} />
            <Route path="observations"  element={<AkteLabCharts />} />
            <Route path="allergies"     element={<AkteEntityList entity="allergies" />} />
            <Route path="events"        element={<AkteEntityList entity="events" />} />
            <Route path="imaging"       element={<AkteEntityList entity="imaging" />} />
            <Route path="practitioners" element={<AkteEntityList entity="practitioners" />} />
            <Route path="documents"     element={<AkteEntityList entity="documents" />} />
            <Route path="notes"         element={<AkteEntityList entity="notes" />} />

            {/* Import */}
            <Route path="import"        element={<ImportView />} />

            {/* Tracking */}
            <Route path="apple"  element={<AppleHealthView />} />
            <Route path="schlaf" element={<AppleHealthView />} />

            {/* KI */}
            <Route path="ki" element={<AppleHealthView />} />
          </Routes>
          <KiFloatingButton />
        </div>
      </div>
    </div>
  )
}