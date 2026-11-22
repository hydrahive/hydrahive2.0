/** Reiter des Föderations-Fensters im Admin-Cockpit (Reiter steht in der URL: `tab=`).
 * „Katalog“ (docs/specs/federation-shared-tasks.md §Oberfläche Cockpit) nach „Server“. */
export const FEDERATION_TABS = ["workstations", "peers", "catalog", "clients", "datamining"] as const
export type FederationTab = (typeof FEDERATION_TABS)[number]

export function parseFederationTab(value: string | null): FederationTab {
  return (FEDERATION_TABS as readonly string[]).includes(value ?? "") ? (value as FederationTab) : "workstations"
}
