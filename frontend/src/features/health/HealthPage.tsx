import { useEffect, useState } from "react"
import { Navigate, Route, Routes } from "react-router-dom"
import { Activity } from "lucide-react"
import { HealthSidebar } from "./HealthSidebar"
import { KiFloatingButton } from "./KiFloatingButton"
import { UebersichtView }  from "./views/UebersichtView"
import { ZeitstrahlView }  from "./views/ZeitstrahlView"
import { DiagnosenView }   from "./views/DiagnosenView"
import { MedikamenteView } from "./views/MedikamenteView"
import { LaborwerteView }  from "./views/LaborwerteView"
import { SimpleListView }  from "./views/SimpleListView"
import { KiAssistentView } from "./views/KiAssistentView"
import { TrendChart }      from "./_TrendChart"
import { SleepChart }      from "./_SleepChart"
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

  return <TrendChart summary={summary} />
}

function SchlafView() {
  const [summary, setSummary] = useState<MetricsSummary | null>(null)

  useEffect(() => {
    healthApi.metrics(30, "sleep_analysis").then(setSummary).catch(() => {
      setSummary({ metrics: {}, last_ingest: null, period_days: 30 })
    })
  }, [])

  if (summary === null) {
    return <div className="h-48 rounded-xl bg-zinc-900/50 animate-pulse" />
  }

  return <SleepChart summary={summary} />
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
          <p className="text-xs text-zinc-500">Digitale Patientenakte</p>
        </div>
      </div>

      <div className="flex gap-6">
        <HealthSidebar />
        <div className="flex-1 min-w-0 relative">
          <Routes>
            <Route index element={<Navigate to="uebersicht" replace />} />
            <Route path="uebersicht"  element={<UebersichtView />} />
            <Route path="zeitstrahl"  element={<ZeitstrahlView />} />
            <Route path="diagnosen"   element={<DiagnosenView />} />
            <Route path="medikamente" element={<MedikamenteView />} />
            <Route path="laborwerte"  element={<LaborwerteView />} />
            <Route path="allergien"   element={<SimpleListView resourceType="AllergyIntolerance" title="Allergien" icon="🤧" />} />
            <Route path="impfungen"   element={<SimpleListView resourceType="Immunization" title="Impfungen" icon="💉" />} />
            <Route path="eingriffe"   element={<SimpleListView resourceType="Procedure" title="Eingriffe" icon="🔪" />} />
            <Route path="arztbesuche" element={<SimpleListView resourceType="Encounter" title="Arztbesuche" icon="🏥" />} />
            <Route path="befunde"     element={<SimpleListView resourceType="DiagnosticReport" title="Befunde" icon="📋" />} />
            <Route path="dokumente"   element={<SimpleListView resourceType="DocumentReference" title="Dokumente" icon="📄" />} />
            <Route path="apple"       element={<AppleHealthView />} />
            <Route path="schlaf"      element={<SchlafView />} />
            <Route path="ki"          element={<KiAssistentView />} />
          </Routes>
          <KiFloatingButton />
        </div>
      </div>
    </div>
  )
}
