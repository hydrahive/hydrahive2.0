import { useEffect, useState } from "react"
import { ChevronRight, FolderPlus, Folder, CornerLeftUp, Check } from "lucide-react"
import { codeGraphApi, type CodeGraphBrowse } from "../codeGraphApi"

/** Navigierbarer Verzeichnis-Browser: erlaubt granulare Auswahl beliebiger
 *  Unterordner (z.B. `sdk/` tief im Baum), nicht nur die Namens-Vorschläge. */
export function GraphDirBrowser({
  projectId, selected, onToggle,
}: {
  projectId: string
  selected: string[]
  onToggle: (rel: string) => void
}) {
  const [browse, setBrowse] = useState<CodeGraphBrowse | null>(null)
  const [path, setPath] = useState("")
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let alive = true
    const load = async () => {
      setLoading(true)
      try {
        const b = await codeGraphApi.browse(projectId, path)
        if (alive) setBrowse(b)
      } catch {
        if (alive) setBrowse({ path, parent: null, dirs: [] })
      } finally {
        if (alive) setLoading(false)
      }
    }
    void load()
    return () => { alive = false }
  }, [projectId, path])

  const crumbs = path ? path.split("/") : []

  return (
    <div className="rounded-[4px] border border-[#2a364b] bg-[#101724] p-3">
      <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.14em] text-[#68758a]">Ordner durchsuchen</p>

      {/* Breadcrumb */}
      <div className="mb-2 flex flex-wrap items-center gap-1 text-[11px] text-[#8d9ab0]">
        <button onClick={() => setPath("")} className="rounded px-1 font-mono hover:text-cyan-200 hover:underline">/</button>
        {crumbs.map((seg, i) => {
          const target = crumbs.slice(0, i + 1).join("/")
          return (
            <span key={target} className="flex items-center gap-1">
              <ChevronRight size={11} className="text-[#46617f]" />
              <button onClick={() => setPath(target)} className="rounded px-0.5 font-mono hover:text-cyan-200 hover:underline">{seg}</button>
            </span>
          )
        })}
      </div>

      {/* Hoch-Navigation */}
      {browse?.parent != null && (
        <button
          onClick={() => setPath(browse.parent ?? "")}
          className="mb-1 flex w-full items-center gap-2 rounded-[3px] px-2 py-1 text-left text-xs text-[#8d9ab0] hover:bg-[#182234]"
        >
          <CornerLeftUp size={13} /> <span className="font-mono">..</span>
        </button>
      )}

      {loading ? (
        <p className="px-2 py-1 text-xs text-[#7a869c]">Lädt…</p>
      ) : browse && browse.dirs.length === 0 ? (
        <p className="px-2 py-1 text-xs text-[#7a869c]">Keine Unterordner.</p>
      ) : (
        <ul className="max-h-[220px] space-y-0.5 overflow-y-auto">
          {browse?.dirs.map((d) => {
            const isSel = selected.includes(d.rel)
            return (
              <li key={d.rel} className="flex items-center gap-1">
                <button
                  onClick={() => onToggle(d.rel)}
                  title={isSel ? "Aus Auswahl entfernen" : "Zum Scan hinzufügen"}
                  className={`grid h-5 w-5 shrink-0 place-items-center rounded-[3px] border ${isSel ? "border-cyan-400/60 bg-cyan-400/20 text-cyan-200" : "border-[#2a364b] text-[#46617f] hover:border-cyan-400/40"}`}
                >
                  {isSel ? <Check size={12} /> : <FolderPlus size={12} />}
                </button>
                <button
                  onClick={() => d.has_children && setPath(d.rel)}
                  disabled={!d.has_children}
                  className={`flex min-w-0 flex-1 items-center gap-1.5 rounded-[3px] px-1.5 py-1 text-left text-xs ${d.has_children ? "text-[#c3ccdd] hover:bg-[#182234]" : "cursor-default text-[#8d9ab0]"}`}
                >
                  <Folder size={13} className="shrink-0 text-[#5f7a94]" />
                  <span className="truncate font-mono">{d.name}</span>
                  {d.has_children && <ChevronRight size={12} className="ml-auto shrink-0 text-[#46617f]" />}
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
