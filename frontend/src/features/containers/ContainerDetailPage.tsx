import { Navigate, useNavigate, useParams } from "react-router-dom"
import { ContainerDetailOverlay } from "@/features/cockpit/admin/ContainerDetailOverlay"
import { useAuthStore } from "@/features/auth/useAuthStore"

/** Legacy deep-link compatibility using the shared Cockpit detail overlay. */
export function ContainerDetailPage() {
  const role = useAuthStore((state) => state.role)
  const navigate = useNavigate()
  const { id } = useParams()

  if (!id) return <Navigate to="/containers" replace />
  if (role === "admin") return <Navigate to={`/admin?section=containers&container=${encodeURIComponent(id)}`} replace />
  return <ContainerDetailOverlay containerId={id} onClose={() => navigate("/containers")} />
}
