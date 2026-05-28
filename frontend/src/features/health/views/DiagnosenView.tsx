import { useEffect, useState } from "react"
import { fhirApi } from "../api"
import { ResourceTable } from "../components/ResourceTable"

interface DiagnoseRow {
  id: string
  name: string
  icd: string
  seit: string
  status: string
}

function parseCondition(r: Record<string, unknown>): DiagnoseRow {
  const code = r.code as Record<string, unknown>
  const codings = (code?.coding as { code?: string; display?: string }[]) ?? []
  const clinicalStatus = r.clinicalStatus as { coding?: { code?: string }[] } | undefined
  const status = clinicalStatus?.coding?.[0]?.code ?? ""
  const onset = (r.onsetDateTime ?? r.onsetString ?? "") as string
  return {
    id: (r.id as string) ?? "",
    name: codings[0]?.display ?? (code?.text as string) ?? "Unbekannt",
    icd: codings[0]?.code ?? "",
    seit: onset.slice(0, 10),
    status,
  }
}

export function DiagnosenView() {
  const [rows, setRows] = useState<DiagnoseRow[] | null>(null)

  useEffect(() => {
    fhirApi.getResources("Condition")
      .then((d) => setRows(d.resources.map((r) => parseCondition(r.resource as Record<string, unknown>))))
      .catch(() => setRows([]))
  }, [])

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-zinc-100">🔴 Diagnosen</h2>
      {rows === null ? <div className="h-32 rounded-xl bg-zinc-900/50 animate-pulse" /> : (
        <ResourceTable
          rows={rows}
          columns={[
            { key: "name", label: "Diagnose" },
            { key: "icd", label: "ICD" },
            { key: "seit", label: "Seit" },
            {
              key: "status", label: "Status",
              render: (r) => (
                <span className={`text-xs px-2 py-0.5 rounded-full ${r.status === "active" ? "bg-red-950 text-red-400" : "bg-zinc-800 text-zinc-400"}`}>
                  {r.status === "active" ? "aktiv" : r.status === "resolved" ? "abgeklungen" : r.status}
                </span>
              ),
            },
          ]}
          emptyText="Keine Diagnosen importiert"
        />
      )}
    </div>
  )
}
