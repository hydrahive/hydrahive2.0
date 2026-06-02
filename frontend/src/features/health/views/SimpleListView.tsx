import { useEffect, useState } from "react"
import { egaApi, type EgaRecord } from "../api"

interface Props {
  dtoType: string
  title: string
  icon: string
}

function summarize(dtoType: string, r: EgaRecord): { primary: string; secondary: string; date: string } {
  const rec = r.record

  if (dtoType === "Encounter") {
    const sp = (rec.serviceProvider ?? {}) as Record<string, unknown>
    const types = (sp.type ?? []) as { text?: string }[]
    const providerName = (sp.name as string) ?? ""
    const providerType = types[0]?.text ?? ""
    return { primary: providerName || providerType || "Arztbesuch", secondary: providerType || "", date: r.sort_date ?? "" }
  }

  if (dtoType === "HospitalStay") {
    const org = (rec.organization ?? {}) as Record<string, unknown>
    const items = (rec.item ?? []) as { service?: { text?: string } }[]
    const desc = items[0]?.service?.text ?? ""
    return { primary: (org.name as string) ?? "Krankenhaus", secondary: desc.slice(0, 80), date: r.sort_date ?? "" }
  }

  if (dtoType === "Procedure") {
    const code = (rec.code ?? {}) as Record<string, unknown>
    const cat = (rec.category ?? {}) as Record<string, unknown>
    return { primary: (code.text as string) ?? r.display, secondary: (cat.text as string) ?? "", date: r.sort_date ?? "" }
  }

  return { primary: r.display, secondary: "", date: r.sort_date ?? "" }
}

export function SimpleListView({ dtoType, title, icon }: Props) {
  const [items, setItems] = useState<ReturnType<typeof summarize>[] | null>(null)

  useEffect(() => {
    egaApi.getRecords(dtoType)
      .then((d) => setItems(d.records.map((r) => summarize(dtoType, r))))
      .catch(() => setItems([]))
  }, [dtoType])

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-zinc-100">{icon} {title}</h2>
      {items === null ? (
        <div className="h-32 rounded-xl bg-zinc-900/50 animate-pulse" />
      ) : items.length === 0 ? (
        <p className="text-zinc-500 text-sm py-8 text-center">Keine {title} importiert.</p>
      ) : (
        <div className="rounded-xl border border-white/[6%] overflow-hidden">
          {items.map((item) => (
            <div key={`${item.date}-${item.primary}-${item.secondary}`} className="px-4 py-3 border-b border-white/[4%] last:border-0 hover:bg-white/[2%]">
              <div className="flex items-center justify-between">
                <span className="text-sm text-zinc-200">{item.primary}</span>
                <span className="text-xs text-zinc-600">{item.date}</span>
              </div>
              {item.secondary && <p className="text-xs text-zinc-500 mt-0.5 truncate">{item.secondary}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
