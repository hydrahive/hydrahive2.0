import { useNavigate } from "react-router-dom"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { AdminRedirect } from "@/features/cockpit/admin/AdminRedirect"
import { FederationOverlay } from "@/features/cockpit/admin/FederationOverlay"

/**
 * Alte Föderations-Seite (Plan alte-seiten-umleiten). Admins → Admin-Fenster. Nutzer mit Freigabe „core.federation“
 * kommen nicht ins Admin-Cockpit; sie bekommen dasselbe Fenster mit Reitern hier (wie SystemPage).
 */
export function FederationPage() {
  const role = useAuthStore((state) => state.role)
  const navigate = useNavigate()
  if (role === "admin") return <AdminRedirect section="federation" />
  return <FederationOverlay onClose={() => navigate("/dashboard")} />
}
