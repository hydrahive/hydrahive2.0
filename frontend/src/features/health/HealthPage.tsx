import { useTranslation } from "react-i18next"
import { Navigate, Route, Routes, useLocation } from "react-router-dom"
import { Activity } from "lucide-react"
import { HealthSidebar } from "./HealthSidebar"
import { KiFloatingButton } from "./KiFloatingButton"
import { AkteErrorBoundary } from "./components/AkteErrorBoundary"
import { AppleHealthView } from "./_AppleHealthView"
import { SchlafView } from "./_SchlafView"

export function HealthPage() {
  const { t } = useTranslation("health")
  const { pathname } = useLocation()
  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-9 h-9 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
          <Activity size={18} className="text-rose-400" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-zinc-100">{t("page_title")}</h1>
          <p className="text-xs text-zinc-500">{t("page_subtitle")}</p>
        </div>
      </div>

      <div className="flex gap-6">
        <HealthSidebar />
        <div className="flex-1 min-w-0 relative">
          <AkteErrorBoundary resetKey={pathname}>
          <Routes>
            <Route index element={<Navigate to="apple" replace />} />

            {/* Tracking */}
            <Route path="apple"  element={<AppleHealthView />} />
            <Route path="schlaf" element={<SchlafView />} />

            {/* KI */}
            <Route path="ki" element={<AppleHealthView />} />
          </Routes>
          </AkteErrorBoundary>
          <KiFloatingButton />
        </div>
      </div>
    </div>
  )
}
