import { useState, useEffect } from "react"
import { ChevronRight, ChevronDown, File, Folder } from "lucide-react"
import { workspaceApi, type TreeEntry } from "./api"

interface Props { agentId: string; path: string; onOpen: (path: string) => void; depth?: number }

export function FileTree({ agentId, path, onOpen, depth = 0 }: Props) {
  const [entries, setEntries] = useState<TreeEntry[] | null>(null)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  useEffect(() => {
    let alive = true
    workspaceApi.tree(agentId, path)
      .then((e) => { if (alive) setEntries(e) })
      .catch(() => { if (alive) setEntries([]) })
    return () => { alive = false }
  }, [agentId, path])

  if (entries === null) return <div className="px-2 py-1 text-[10px] text-zinc-600">…</div>

  return (
    <div>
      {entries.map((e) => {
        const childPath = path ? `${path}/${e.name}` : e.name
        const isOpen = expanded.has(e.name)
        return (
          <div key={e.name}>
            <button
              onClick={() => e.is_dir
                ? setExpanded((s) => { const n = new Set(s); n.has(e.name) ? n.delete(e.name) : n.add(e.name); return n })
                : onOpen(childPath)}
              className="w-full flex items-center gap-1 px-1.5 py-0.5 text-[11px] text-zinc-400 hover:bg-white/[4%] rounded text-left"
              style={{ paddingLeft: `${6 + depth * 12}px` }}
            >
              {e.is_dir ? (isOpen ? <ChevronDown size={11} className="shrink-0" /> : <ChevronRight size={11} className="shrink-0" />) : <span className="w-[11px] shrink-0" />}
              {e.is_dir ? <Folder size={11} className="text-violet-400/70 shrink-0" /> : <File size={11} className="text-zinc-500 shrink-0" />}
              <span className="truncate">{e.name}</span>
            </button>
            {e.is_dir && isOpen && <FileTree agentId={agentId} path={childPath} onOpen={onOpen} depth={depth + 1} />}
          </div>
        )
      })}
    </div>
  )
}
