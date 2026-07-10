import { CockpitPlaceholderPage } from "./CockpitPlaceholderPage"

export function VaultCockpitPage() {
  return (
    <CockpitPlaceholderPage
      kind="vault"
      eyebrow="Vault"
      title="Vault-Cockpit"
      description="Private und sensible Bereiche wie Patientenakte, Crypto, Dokumente, Finanzen und persönliche Notizen."
      mockupPath="/mockups/vault-cockpit-v1/index.html"
      bullets={[
        "Patientenakte und Crypto zusammenführen",
        "Dokumente, Uploads und Suche vorbereiten",
        "Vault-Chat mit Kontextschutz",
        "sensible Daten nicht automatisch weiterreichen",
      ]}
    />
  )
}
