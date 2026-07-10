import { useCallback, useEffect, useState } from "react"
import { File, Folder, Plus, Search, Upload } from "lucide-react"
import { CockpitButton } from "../CockpitButton"
import { CockpitPanel, CockpitSectionLabel } from "../CockpitPanel"
import { projectsApi } from "@/features/projects/api"
import { classifyFile, type FileKind } from "@/features/chat/workspace/fileType"

interface ProjectFileEntry {
  name: string
  type: "file" | "dir"
  size: number | null
  modified: number
}

interface Props {
  projectId: string | null
  onOpenFile: (path: string, kind: FileKind) => void
}

function formatSize(size: number | null) {
  if (size == null) return "dir"
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

export function ProjectWorkspacePanel({ projectId, onOpenFile }: Props) {
  const [path, setPath] = useState("")
  const [entries, setEntries] = useState<ProjectFileEntry[]>([])
  const [query, setQuery] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    if (!projectId) {
      setEntries([])
      return
    }
    setLoading(true)
    setError(null)
    try {
      const result = await projectsApi.listFiles(projectId, path)
      setEntries(result.entries)
    } catch {
      setEntries([])
      setError("Workspace konnte nicht geladen werden.")
    } finally {
      setLoading(false)
    }
  }, [projectId, path])

  useEffect(() => { void reload() }, [reload])

  const filtered = entries.filter((entry) => entry.name.toLowerCase().includes(query.toLowerCase()))
  const parentPath = path.split("/").slice(0, -1).join("/")

  return (
    <CockpitPanel className="flex min-h-0 flex-col p-3">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <CockpitSectionLabel>Dateimanager</CockpitSectionLabel>
          <h2 className="truncate text-sm font-bold text-[#e8eef8]">Workspace</h2>
        </div>
        <CockpitButton disabled={!projectId} onClick={() => void reload()}>
          <Upload size={12} className="mr-1 inline" /> Upload
        </CockpitButton>
      </div>

      <div className="mb-2 flex gap-1.5">
        <label className="flex min-w-0 flex-1 items-center gap-2 rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-2 py-1.5 text-xs text-[#8d9ab0]">
          <Search size={12} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Datei suchen…"
            className="min-w-0 flex-1 bg-transparent text-[#e8eef8] outline-none placeholder:text-[#8d9ab0]"
          />
        </label>
        <CockpitButton disabled={!projectId}><Plus size={12} className="mr-1 inline" /> Neu</CockpitButton>
      </div>

      {path && (
        <button
          type="button"
          onClick={() => setPath(parentPath)}
          className="mb-2 w-full rounded-[4px] border border-[#2a364b] bg-[#111827] px-2 py-1 text-left text-xs text-[#8d9ab0] hover:border-[#46617f] hover:text-[#e8eef8]"
        >
          ../ {parentPath || "Projektwurzel"}
        </button>
      )}

      {error ? <p className="mb-2 text-xs text-rose-300">{error}</p> : null}
      {loading ? <p className="text-xs text-[#8d9ab0]">Lade Workspace…</p> : null}

      <div className="min-h-0 flex-1 overflow-y-auto rounded-[4px] border border-[#223048] bg-[#111827]">
        {!loading && filtered.length === 0 ? <p className="p-2 text-xs text-[#8d9ab0]">Keine Dateien gefunden.</p> : null}
        {filtered.map((entry) => {
          const childPath = path ? `${path}/${entry.name}` : entry.name
          return (
            <button
              key={`${entry.type}:${entry.name}`}
              type="button"
              onClick={() => entry.type === "dir" ? setPath(childPath) : onOpenFile(childPath, classifyFile(childPath))}
              className="flex w-full items-center justify-between gap-2 border-b border-[#223048] px-2 py-1.5 text-left text-xs text-[#d8e0ec] hover:bg-[#172133]"
            >
              <span className="flex min-w-0 items-center gap-2">
                {entry.type === "dir" ? <Folder size={13} className="shrink-0 text-[#69d7ff]/75" /> : <File size={13} className="shrink-0 text-[#8d9ab0]" />}
                <span className="truncate">{entry.name}{entry.type === "dir" ? "/" : ""}</span>
              </span>
              <span className="shrink-0 text-[11px] text-[#8d9ab0]">{formatSize(entry.size)}</span>
            </button>
          )
        })}
      </div>
    </CockpitPanel>
  )
}
