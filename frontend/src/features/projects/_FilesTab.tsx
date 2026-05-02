import { ChevronRight, File, Folder, Loader2 } from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"

interface Entry { name: string; type: "file" | "dir"; size: number | null; modified: number }

interface Props { projectId: string }

export function FilesTab({ projectId }: Props) {
  const { t } = useTranslation("projects")
  const [path, setPath] = useState("")
  const [entries, setEntries] = useState<Entry[]>([])
  const [loading, setLoading] = useState(false)
  const [fileContent, setFileContent] = useState<string | null>(null)
  const [openFile, setOpenFile] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function loadDir(p: string) {
    setLoading(true); setError(null); setFileContent(null); setOpenFile(null)
    try {
      const res = await projectsApi.listFiles(projectId, p)
      setPath(res.path); setEntries(res.entries)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler")
    } finally { setLoading(false) }
  }

  async function openFileEntry(name: string) {
    const filePath = path ? `${path}/${name}` : name
    setLoading(true); setError(null)
    try {
      const content = await projectsApi.readFile(projectId, filePath)
      setFileContent(content); setOpenFile(name)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler")
    } finally { setLoading(false) }
  }

  function navigateUp() {
    const parts = path.split("/").filter(Boolean)
    parts.pop()
    loadDir(parts.join("/"))
  }

  useEffect(() => { loadDir("") }, [projectId])

  const breadcrumbs = ["root", ...path.split("/").filter(Boolean)]

  return (
    <div className="space-y-3">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1 text-xs text-zinc-500">
        {breadcrumbs.map((part, i) => (
          <span key={i} className="flex items-center gap-1">
            {i > 0 && <ChevronRight size={10} />}
            <button
              onClick={() => loadDir(breadcrumbs.slice(1, i + 1).join("/"))}
              className="hover:text-zinc-200 transition-colors"
            >
              {part}
            </button>
          </span>
        ))}
        {loading && <Loader2 size={11} className="animate-spin ml-1" />}
      </div>

      {error && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/[6%] px-3 py-2 text-xs text-rose-300">{error}</div>
      )}

      {/* File viewer */}
      {fileContent !== null ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-400 font-mono">{openFile}</span>
            <button onClick={() => setFileContent(null)} className="text-xs text-zinc-500 hover:text-zinc-200">✕ {t("files.close")}</button>
          </div>
          <pre className="rounded-lg border border-white/[8%] bg-zinc-900 p-3 text-xs text-zinc-300 font-mono overflow-auto max-h-[500px] whitespace-pre-wrap break-words">
            {fileContent}
          </pre>
        </div>
      ) : (
        <div className="rounded-lg border border-white/[8%] overflow-hidden">
          {path && (
            <button
              onClick={navigateUp}
              className="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/[3%] text-xs text-zinc-400 border-b border-white/[6%]"
            >
              <Folder size={13} className="text-zinc-500" /> ..
            </button>
          )}
          {entries.length === 0 && !loading && (
            <p className="text-xs text-zinc-600 text-center py-6">{t("files.empty")}</p>
          )}
          {entries.map((e) => (
            <button
              key={e.name}
              onClick={() => e.type === "dir" ? loadDir(path ? `${path}/${e.name}` : e.name) : openFileEntry(e.name)}
              className="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/[3%] text-xs text-left border-b border-white/[4%] last:border-0"
            >
              {e.type === "dir"
                ? <Folder size={13} className="text-amber-400 flex-shrink-0" />
                : <File size={13} className="text-zinc-500 flex-shrink-0" />}
              <span className={`flex-1 truncate ${e.type === "dir" ? "text-zinc-200" : "text-zinc-400"}`}>{e.name}</span>
              {e.size !== null && (
                <span className="text-zinc-600 flex-shrink-0">{e.size < 1024 ? `${e.size}B` : `${(e.size / 1024).toFixed(1)}KB`}</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
