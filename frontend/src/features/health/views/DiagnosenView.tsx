import { useEffect, useState } from "react"
import { egaApi, type EgaRecord } from "../api"
import { ResourceTable } from "../components/ResourceTable"

interface DiagnoseRow extends Record<string, unknown> {
  id: string
  name: string
  icd: string
  system: string
}

function parseDiagnose(r: EgaRecord): DiagnoseRow {
  const code = (r.record.code ?? {}) as Record<string, unknown>
  const codings = (code.coding ?? []) as { code?: string; display?: string; system?: string }[]
  const icd = codings[0] ?? {}
  return {
    id: r.id,
    name: icd.display ?? (code.text as string) ?? r.display,
    icd: icd.code ?? "",
    system: icd.system?.includes("icd-10-gm") ? "ICD-10-GM" : (icd.system ?? ""),
  }
}

export function DiagnosenView() {
  const [rows, setRows] = useState<DiagnoseRow[] | null>(null)

  useEffect(() => {
    egaApi.getRecords("Condition")
      .then((d) => setRows(d.records.map(parseDiagnose)))
      .catch(() => setRows([]))
  }, [])

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-zinc-100">📋 Diagnosen</h2>
      {rows === null ? <div className="h-32 rounded-xl bg-zinc-900/50 animate-pulse" /> : (
        <ResourceTable
          rows={rows}
          columns={[
            { key: "name", label: "Diagnose" },
            { key: "icd", label: "ICD-Code" },
            { key: "system", label: "System" },
          ]}
          emptyText="Keine Diagnosen importiert"
        />
      )}
    </div>
  )
}
