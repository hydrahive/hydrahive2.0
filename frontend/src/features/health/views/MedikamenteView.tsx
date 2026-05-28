import { useEffect, useState } from "react"
import { fhirApi } from "../api"
import { ResourceTable } from "../components/ResourceTable"

interface MedRow { id: string; name: string; status: string; datum: string }

function parseMed(r: Record<string, unknown>): MedRow {
  const med = (r.medicationCodeableConcept ?? r.medicationReference ?? {}) as Record<string, unknown>
  const name = (med.text ?? med.display ?? "Unbekannt") as string
  return {
    id: (r.id as string) ?? "",
    name,
    status: (r.status ?? "") as string,
    datum: ((r.authoredOn ?? r.dateAsserted ?? "") as string).slice(0, 10),
  }
}

export function MedikamenteView() {
  const [rows, setRows] = useState<MedRow[] | null>(null)

  useEffect(() => {
    Promise.all([
      fhirApi.getResources("MedicationRequest"),
      fhirApi.getResources("MedicationStatement"),
    ]).then(([a, b]) => {
      const all = [...a.resources, ...b.resources].map((r) => parseMed(r.resource as Record<string, unknown>))
      setRows(all)
    }).catch(() => setRows([]))
  }, [])

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-zinc-100">💊 Medikamente</h2>
      {rows === null ? <div className="h-32 rounded-xl bg-zinc-900/50 animate-pulse" /> : (
        <ResourceTable
          rows={rows}
          columns={[
            { key: "name", label: "Medikament" },
            { key: "status", label: "Status" },
            { key: "datum", label: "Datum" },
          ]}
          emptyText="Keine Medikamente importiert"
        />
      )}
    </div>
  )
}
