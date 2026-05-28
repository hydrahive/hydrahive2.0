import { Navigate, Route, Routes } from "react-router-dom"
import { Activity } from "lucide-react"
import { HealthSidebar } from "./HealthSidebar"

// These components will be created in Tasks 9-11
// Import them now so routing is wired up

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
            {/* Views will be added in Tasks 9-11 */}
            <Route path="*" element={<div className="text-zinc-500 text-sm py-8 text-center">Wird geladen…</div>} />
          </Routes>
        </div>
      </div>
    </div>
  )
}
