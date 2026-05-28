import { useEffect, useState } from "react"
import { egaApi, type EgaRecord } from "../api"
import { ResourceTable } from "../components/ResourceTable"

interface MedRow extends Record<string, unknown> {
  id: string
  name: string
  wirkstoff: string
  atc: string
  datum: string
}

function parseMed(r: EgaRecord): MedRow {
  const med = (r.record.medication ?? {}) as Record<string, unknown>
  const code = (med.code ?? {}) as Record<string, unknown>
  const name = (code.text as string) ?? r.display

  const ingredients = (med.ingredient ?? []) as Record<string, unknown>[]
  const ing0 = ingredients[0] ?? {}
  const ic = (ing0.itemCodeableConcept ?? {}) as Record<string, unknown>
  const wirkstoff = (ic.text as string) ?? ""
  const ingCodings = (ic.coding ?? []) as { system?: string; code?: string }[]
  const atcCode = ingCodings.find((c) => c.system?.includes("atc"))?.code ?? ""

  return { id: r.id, name, wirkstoff, atc: atcCode, datum: r.sort_date ?? "" }
}

export function MedikamenteView() {
  const [rows, setRows] = useState<MedRow[] | null>(null)

  useEffect(() => {
    egaApi.getRecords("MedicationDispense")
      .then((d) => setRows(d.records.map(parseMed)))
      .catch(() => setRows([]))
  }, [])

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-zinc-100">💊 Medikamente</h2>
      {rows === null ? <div className="h-32 rounded-xl bg-zinc-900/50 animate-pulse" /> : (
        <ResourceTable
          rows={rows}
          columns={[
            { key: "name", label: "Medikament" },
            { key: "wirkstoff", label: "Wirkstoff" },
            { key: "atc", label: "ATC" },
            { key: "datum", label: "Datum" },
          ]}
          emptyText="Keine Medikamente importiert"
        />
      )}
    </div>
  )
}
