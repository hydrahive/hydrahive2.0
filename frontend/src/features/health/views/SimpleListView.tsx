import { useEffect, useState } from "react"
import { fhirApi } from "../api"

interface Props {
  resourceType: string
  title: string
  icon: string
}

function summarize(r: Record<string, unknown>): string {
  const tryPaths: (() => string | undefined)[] = [
    () => (r.code as Record<string, unknown>)?.text as string,
    () => ((r.code as Record<string, unknown>)?.coding as { display?: string }[])?.[0]?.display,
    () => (r.vaccineCode as Record<string, unknown>)?.text as string,
    () => (r.class as Record<string, unknown>)?.display as string,
    () => (r.type as { text?: string }[])?.[0]?.text,
    () => r.id as string,
  ]
  for (const fn of tryPaths) {
    try {
      const v = fn()
      if (v) return v
    } catch {
      // skip
    }
  }
  return JSON.stringify(r).slice(0, 80)
}

export function SimpleListView({ resourceType, title, icon }: Props) {
  const [items, setItems] = useState<string[] | null>(null)

  useEffect(() => {
    fhirApi.getResources(resourceType)
      .then((d) => setItems(d.resources.map((r) => summarize(r.resource as Record<string, unknown>))))
      .catch(() => setItems([]))
  }, [resourceType])

  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-zinc-100">{icon} {title}</h2>
      {items === null ? (
        <div className="h-32 rounded-xl bg-zinc-900/50 animate-pulse" />
      ) : items.length === 0 ? (
        <p className="text-zinc-500 text-sm py-8 text-center">Keine {title} importiert.</p>
      ) : (
        <div className="rounded-xl border border-white/[6%] overflow-hidden">
          {items.map((item, i) => (
            <div key={i} className="px-4 py-3 border-b border-white/[4%] last:border-0 text-sm text-zinc-300 hover:bg-white/[2%]">
              {item}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
