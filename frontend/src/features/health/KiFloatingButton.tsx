import { MessageCircle } from "lucide-react"
import { useNavigate, useLocation } from "react-router-dom"

const ROUTE_TO_LABEL: Record<string, string> = {
  "/health/diagnosen":   "Diagnosen",
  "/health/medikamente": "Medikamente",
  "/health/laborwerte":  "Laborwerte",
  "/health/allergien":   "Allergien",
  "/health/impfungen":   "Impfungen",
  "/health/eingriffe":   "Eingriffe",
  "/health/arztbesuche": "Arztbesuche",
  "/health/befunde":     "Befunde",
}

const ROUTE_TO_RESOURCE_TYPE: Record<string, string> = {
  "/health/diagnosen":   "Condition",
  "/health/medikamente": "MedicationRequest",
  "/health/laborwerte":  "Observation",
  "/health/allergien":   "AllergyIntolerance",
  "/health/impfungen":   "Immunization",
  "/health/eingriffe":   "Procedure",
  "/health/arztbesuche": "Encounter",
  "/health/befunde":     "DiagnosticReport",
}

export function KiFloatingButton() {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const resourceType = ROUTE_TO_RESOURCE_TYPE[pathname]
  const categoryLabel = ROUTE_TO_LABEL[pathname]

  if (pathname === "/health/ki") return null

  const label = categoryLabel ? `KI zu ${categoryLabel} fragen` : "KI fragen"

  return (
    <button
      onClick={() => navigate("/health/ki", { state: { resourceType } })}
      className="fixed bottom-6 right-6 flex items-center gap-2 px-4 py-2.5 rounded-full bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium shadow-lg shadow-indigo-900/40 transition-all hover:scale-105"
    >
      <MessageCircle size={16} />
      {label}
    </button>
  )
}
