import { useEffect, useState, type CSSProperties } from "react"
import { egaApi, type EgaRecord } from "../api"
import { rgbFor } from "@/shared/colors"

interface AbrechnungRow {
  id: string
  arzt: string
  ort: string
  quartal: string
  diagnosen: string[]
  kosten: string
}

function parseAbrechnung(r: EgaRecord): AbrechnungRow {
  const org = (r.record.organization ?? {}) as Record<string, unknown>
  const addresses = (org.address ?? []) as Record<string, unknown>[]
  const addr = addresses[0] ?? {}
  const ort = [addr.postalCode, addr.city].filter(Boolean).join(" ")

  const bp = (r.record.billablePeriod ?? {}) as Record<string, unknown>
  const quartal = (bp.start as string)?.slice(0, 7) ?? ""

  const diagnoses = (r.record.diagnosis ?? []) as Record<string, unknown>[]
  const diagnosen = diagnoses
    .flatMap((d) => {
      const dcc = (d.diagnosisCodeableConcept ?? {}) as Record<string, unknown>
      const codings = (dcc.coding ?? []) as { code?: string }[]
      return codings.map((c) => c.code ?? "").filter(Boolean)
    })
    .slice(0, 6)

  const total = (r.record.total ?? {}) as { value?: number }
  const kosten = total.value != null ? `${total.value.toFixed(2)} €` : ""

  return { id: r.id, arzt: (org.name as string) ?? "Unbekannt", ort, quartal, diagnosen, kosten }
}

export function ArztabrechnungView() {
  const [rows, setRows] = useState<AbrechnungRow[] | null>(null)

  useEffect(() => {
    egaApi.getRecords("AmbulantClaim")
      .then((d) => setRows(d.records.map(parseAbrechnung)))
      .catch(() => setRows([]))
  }, [])

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-zinc-100">🧾 Arztabrechnungen</h2>
      {rows === null ? (
        <div className="h-32 rounded-xl bg-zinc-900/50 animate-pulse" />
      ) : rows.length === 0 ? (
        <p className="text-zinc-500 text-sm py-8 text-center">Keine Abrechnungen importiert.</p>
      ) : (
        <div className="box overflow-hidden" style={{ "--c": rgbFor("/health") } as CSSProperties}>
          {rows.map((row) => (
            <div key={row.id} className="px-4 py-3 border-b border-white/[4%] last:border-0 hover:bg-white/[2%]">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <span className="text-sm text-zinc-200 font-medium">{row.arzt}</span>
                  {row.ort && <span className="text-xs text-zinc-500 ml-2">{row.ort}</span>}
                </div>
                <div className="text-right shrink-0">
                  {row.quartal && <div className="text-xs text-zinc-500">{row.quartal}</div>}
                  {row.kosten && <div className="text-xs text-emerald-500 mt-0.5">{row.kosten}</div>}
                </div>
              </div>
              {row.diagnosen.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1.5">
                  {row.diagnosen.map((d) => (
                    <span key={d} className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">{d}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
