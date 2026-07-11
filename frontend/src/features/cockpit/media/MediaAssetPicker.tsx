import { Check, ImageOff } from "lucide-react"
import type { MediaAssetReference } from "../mediaProjectsApi"

export function MediaAssetPicker({ assets, selected, onToggle, emptyLabel }: {
  assets: MediaAssetReference[]
  selected: string[]
  onToggle: (id: string) => void
  emptyLabel: string
}) {
  const unknown = selected.filter((id) => !assets.some((asset) => asset.id === id))
  if (!assets.length && !unknown.length) return <p className="rounded-[3px] border border-dashed border-[#2a364b] p-3 text-xs text-[#718097]">{emptyLabel}</p>

  return <div className="grid gap-2 sm:grid-cols-2">
    {assets.map((asset) => {
      const active = selected.includes(asset.id)
      return <button key={asset.id} type="button" disabled={!asset.available && !active} onClick={() => onToggle(asset.id)} className={`flex min-w-0 items-start gap-2 rounded-[3px] border p-2 text-left ${active ? "border-[#69d7ff] bg-[#163047]" : "border-[#2a364b] bg-[#101724]"} disabled:cursor-not-allowed disabled:opacity-50`}>
        <span className={`mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded border ${active ? "border-[#69d7ff] bg-[#69d7ff] text-[#08111c]" : "border-[#46617f]"}`}>{active && <Check size={11} />}</span>
        <span className="min-w-0"><strong className="block truncate text-xs text-[#e8eef8]">{asset.label}</strong><span className="block truncate text-[10px] text-[#718097]">{asset.kind} · {asset.rel_path}</span>{!asset.available && <span className="mt-1 flex items-center gap-1 text-[10px] text-amber-300"><ImageOff size={10} />Quelle nicht verfügbar</span>}</span>
      </button>
    })}
    {unknown.map((id) => <button key={id} type="button" onClick={() => onToggle(id)} className="flex items-start gap-2 rounded-[3px] border border-amber-500/30 bg-amber-500/5 p-2 text-left"><span className="mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded border border-[#69d7ff] bg-[#69d7ff] text-[#08111c]"><Check size={11} /></span><span className="min-w-0"><strong className="block truncate text-xs text-amber-200">Unbekannte Referenz</strong><span className="block truncate text-[10px] text-[#718097]">{id} · zum Entfernen anklicken</span></span></button>)}
  </div>
}
