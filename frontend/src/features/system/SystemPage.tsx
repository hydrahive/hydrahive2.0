import { Navigate } from "react-router-dom"

/**
 * Legacy route compatibility: all system entry points converge on the same
 * Admin-Cockpit overlay instead of maintaining a second visual implementation.
 */
export function SystemPage() {
  return <Navigate to="/admin?section=system" replace />
}
