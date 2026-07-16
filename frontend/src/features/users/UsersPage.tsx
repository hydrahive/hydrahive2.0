import { Navigate } from "react-router-dom"

/** Legacy route compatibility without a second user-management UI. */
export function UsersPage() {
  return <Navigate to="/admin?section=users" replace />
}
