import { useId, useMemo, useState, type KeyboardEvent } from "react"
import { ChevronDown, Plus, Search } from "lucide-react"
import { filterItems, type PickerItem } from "./pickerFilter"

interface Props {
  label: string
  items: PickerItem[]
  value: string | null
  onChange: (id: string) => void
  /** Wenn gesetzt: Knopf „+ Neu“ neben dem Feld. */
  onCreate?: () => void
}

/** Auswahlfeld mit Suche (Combobox) für Agenten/Projekte – ersetzt die lange Liste am Rand. */
export function ItemPicker({ label, items, value, onChange, onCreate }: Props) {
  const id = useId()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")
  const [hi, setHi] = useState(0)
  const current = items.find((i) => i.id === value) ?? null
  const hits = useMemo(() => filterItems(items, query), [items, query])

  function pick(item: PickerItem) {
    onChange(item.id); setOpen(false); setQuery("")
  }
  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") { e.preventDefault(); setOpen(true); setHi((h) => Math.min(h + 1, hits.length - 1)) }
    else if (e.key === "ArrowUp") { e.preventDefault(); setHi((h) => Math.max(h - 1, 0)) }
    else if (e.key === "Enter" && open && hits[hi]) { e.preventDefault(); pick(hits[hi]) }
    else if (e.key === "Escape") { setOpen(false); setQuery("") }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <label htmlFor={id} className="text-[10px] font-black uppercase tracking-[0.14em] text-[#69d7ff]">{label}</label>
      {items.length === 0 ? (
        <span className="text-sm text-[#9aa7bc]">Keine Einträge</span>
      ) : (
        <div className="relative min-w-0 flex-1 sm:max-w-md">
          <Search size={13} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[#9aa7bc]" />
          <input
            id={id}
            role="combobox"
            aria-expanded={open}
            aria-controls={`${id}-list`}
            aria-autocomplete="list"
            aria-activedescendant={open && hits[hi] ? `${id}-opt-${hits[hi].id}` : undefined}
            autoComplete="off"
            value={open ? query : current?.name ?? ""}
            placeholder={current ? current.name : "Suchen …"}
            onFocus={() => { setOpen(true); setHi(0) }}
            onBlur={() => setTimeout(() => { setOpen(false); setQuery("") }, 120)}
            onChange={(e) => { setQuery(e.target.value); setOpen(true); setHi(0) }}
            onKeyDown={onKey}
            className="w-full rounded-[4px] border border-s-rand bg-s-tief py-1.5 pl-8 pr-8 text-sm font-semibold text-[#e8eef8] outline-none placeholder:font-normal placeholder:text-[#9aa7bc] hover:border-s-rand-hover focus:border-[#69d7ff]/60"
          />
          <ChevronDown size={14} className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-[#9aa7bc]" />
          {!open && current?.detail && <p className="mt-0.5 truncate text-[11px] text-[#9aa7bc]">{current.detail}</p>}
          {open && (
            <ul id={`${id}-list`} role="listbox" className="absolute z-30 mt-1 max-h-72 w-full overflow-y-auto rounded-[4px] border border-s-rand bg-s-box p-1 shadow-2xl">
              {hits.length === 0 && <li className="px-3 py-2 text-xs text-[#9aa7bc]">Kein Treffer</li>}
              {hits.map((item, i) => (
                <li key={item.id} id={`${id}-opt-${item.id}`} role="option" aria-selected={item.id === value}
                  onMouseDown={(e) => { e.preventDefault(); pick(item) }} onMouseEnter={() => setHi(i)}
                  className={`cursor-pointer rounded-[3px] px-3 py-1.5 ${i === hi ? "bg-[#1c2940]" : ""} ${item.dim ? "opacity-50" : ""}`}>
                  <p className={`truncate text-sm ${item.id === value ? "font-bold text-[#69d7ff]" : "text-[#e8eef8]"}`}>{item.name}</p>
                  {item.detail && <p className="truncate text-[11px] text-[#9aa7bc]">{item.detail}</p>}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {onCreate && (
        <button type="button" onClick={onCreate}
          className="flex items-center gap-1 rounded-[4px] border border-[#69d7ff]/35 bg-[#163248] px-2.5 py-1.5 text-xs font-semibold text-[#c8f2ff] hover:bg-[#1b3d56]">
          <Plus size={12} /> Neu
        </button>
      )}
    </div>
  )
}
