import { useEffect, useState } from "react"
import { fhirApi } from "../api"
import { ResourceTable } from "../components/ResourceTable"

interface LabRow extends Record<string, unknown> { id: string; name: string; wert: string; datum: string }

function parseLab(r: Record<string, unknown>): LabRow {
  const code = r.code as Record<string, unknown>
  const codings = (code?.coding as { display?: string }[]) ?? []
  const name = (code?.text as string) ?? codings[0]?.display ?? ""
  const vq = r.valueQuantity as Record<string, unknown> | undefined
  const wert = vq ? `${vq.value} ${vq.unit ?? ""}`.trim() : (r.valueString ?? "") as string
  return {
    id: (r.id as string) ?? "",
    name,
    wert,
    datum: ((r.effectiveDateTime ?? "") as string).slice(0, 10),
  }
}

export function LaborwerteView() {
  const [rows, setRows] = useState<LabRow[] | null>(null)

  useEffect(() => {
    fhirApi.getResources("Observation")
      .then((d) => setRows(d.resources.map((r) => parseLab(r.resource as Record<string, unknown>))))
      .catch(() => setRows([]))
  }, [])

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-zinc-100">🧪 Laborwerte</h2>
      {rows === null ? <div className="h-32 rounded-xl bg-zinc-900/50 animate-pulse" /> : (
        <ResourceTable
          rows={rows}
          columns={[
            { key: "name", label: "Parameter" },
            { key: "wert", label: "Wert" },
            { key: "datum", label: "Datum" },
          ]}
          emptyText="Keine Laborwerte importiert"
        />
      )}
    </div>
  )
}
