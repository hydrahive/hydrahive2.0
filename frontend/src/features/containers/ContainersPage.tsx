import { Navigate, useNavigate } from "react-router-dom"
import { ContainersOverlay } from "@/features/cockpit/admin/ContainersOverlay"
import { useAuthStore } from "@/features/auth/useAuthStore"

/** Legacy route compatibility without maintaining a second container UI. */
export function ContainersPage() {
  const role = useAuthStore((state) => state.role)
  const navigate = useNavigate()

  if (role === "admin") return <Navigate to="/admin?section=containers" replace />
  return (
    <ContainersOverlay
      onClose={() => navigate("/dashboard")}
      onSelectContainer={(containerId) => {
        if (containerId) navigate(`/containers/${encodeURIComponent(containerId)}`)
      }}
    />
  )
}
