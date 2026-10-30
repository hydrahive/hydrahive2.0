import { Navigate, useLocation } from "react-router-dom"
import type { AdminOverlayId } from "./adminOverlayRegistry"

/**
 * Alte Seite → Admin-Fenster (Plan alte-seiten-umleiten, „jede Einstellung hat nur ein Zuhause“).
 * Der Reiter (`tab=`) und andere Werte der alten Adresse werden mitgenommen.
 */
export function AdminRedirect({ section }: { section: AdminOverlayId }) {
  const { search } = useLocation()
  const params = new URLSearchParams(search)
  params.delete("section")
  const rest = params.toString()
  return <Navigate to={`/admin?section=${section}${rest ? `&${rest}` : ""}`} replace />
}
