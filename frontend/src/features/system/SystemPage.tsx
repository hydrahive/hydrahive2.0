import { Navigate, useNavigate } from "react-router-dom"
import { SystemOverlay } from "@/features/cockpit/admin/SystemOverlay"
import { useAuthStore } from "@/features/auth/useAuthStore"

/**
 * Legacy route compatibility without a second visual implementation. Admins
 * deep-link into the cockpit; other authenticated roles retain their previous
 * read-only system access through the same shared overlay content.
 */
export function SystemPage() {
  const role = useAuthStore((state) => state.role)
  const navigate = useNavigate()

  if (role === "admin") return <Navigate to="/admin?section=system" replace />
  return <SystemOverlay onClose={() => navigate("/dashboard")} />
}
