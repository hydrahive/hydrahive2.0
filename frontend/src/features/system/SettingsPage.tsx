import { Navigate } from "react-router-dom"

/** Legacy route compatibility for bookmarks and settings-hub links. */
export function SettingsPage() {
  return <Navigate to="/admin?section=system-settings" replace />
}
