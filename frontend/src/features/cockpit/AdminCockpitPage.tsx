import { CockpitPlaceholderPage } from "./CockpitPlaceholderPage"

export function AdminCockpitPage() {
  return (
    <CockpitPlaceholderPage
      kind="admin"
      eyebrow="Admin"
      title="Admin-Cockpit"
      description="Systemstatus, User/Rollen, Module, Integrationen, Credentials, Logs und Wartung an einem Ort."
      mockupPath="/mockups/admin-cockpit-v1/index.html"
      bullets={[
        "AdminGuard schützt die Route",
        "User, Rollen und Rechte zentral verwalten",
        "Module, Extensions, Plugins und Credentials bündeln",
        "gefährliche Aktionen mit Tool-Confirm absichern",
      ]}
    />
  )
}
