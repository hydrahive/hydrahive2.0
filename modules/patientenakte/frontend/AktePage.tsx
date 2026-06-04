import { useTranslation } from "react-i18next"
import { Navigate, Route, Routes, useLocation } from "react-router-dom"
import { FolderHeart } from "lucide-react"
import { AkteSidebar } from "./AkteSidebar"
import { AkteErrorBoundary } from "./components/AkteErrorBoundary"
import { AkteDashboard } from "./views/AkteDashboard"
import { AkteTimeline } from "./views/AkteTimeline"
import { AkteEntityList } from "./views/AkteEntityList"
import { AkteLabCharts } from "./views/AkteLabCharts"
import { ImportView } from "./views/ImportView"

export function AktePage() {
  const { t } = useTranslation("akte")
  const { pathname } = useLocation()
  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-9 h-9 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
          <FolderHeart size={18} className="text-rose-400" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-zinc-100">{t("page_title")}</h1>
          <p className="text-xs text-zinc-500">{t("page_subtitle")}</p>
        </div>
      </div>

      <div className="flex gap-6">
        <AkteSidebar />
        <div className="flex-1 min-w-0 relative">
          <AkteErrorBoundary resetKey={pathname}>
            <Routes>
              <Route index element={<Navigate to="uebersicht" replace />} />
              <Route path="uebersicht"     element={<AkteDashboard />} />
              <Route path="timeline"       element={<AkteTimeline />} />
              <Route path="conditions"     element={<AkteEntityList entity="conditions" />} />
              <Route path="medications"    element={<AkteEntityList entity="medications" />} />
              <Route path="observations"   element={<AkteLabCharts />} />
              <Route path="allergies"      element={<AkteEntityList entity="allergies" />} />
              <Route path="events"         element={<AkteEntityList entity="events" />} />
              <Route path="imaging"        element={<AkteEntityList entity="imaging" />} />
              <Route path="practitioners"  element={<AkteEntityList entity="practitioners" />} />
              <Route path="documents"      element={<AkteEntityList entity="documents" />} />
              <Route path="notes"          element={<AkteEntityList entity="notes" />} />
              <Route path="import"         element={<ImportView />} />
            </Routes>
          </AkteErrorBoundary>
        </div>
      </div>
    </div>
  )
}
