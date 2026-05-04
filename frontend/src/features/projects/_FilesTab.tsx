import { ChevronRight, File, Folder, Loader2, Pencil, Save, Trash2, Upload, X } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"

interface Entry { name: string; type: "file" | "dir"; size: number | null; modified: number }

interface Props { projectId: string }

export function FilesTab({ projectId }: Props) {
  const { t } = useTranslation("projects")
  const [path, setPath] = useState("")
  const [entries, setEntries] = useState<Entry[]>([])
  const [loading, setLoading] = useState(false)
  const [openFile, setOpenFile] = useState<string | null>(null)
  const [savedContent, setSavedContent] = useState<string>("")
  const [editContent, setEditContent] = useState<string>("")
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const uploadRef = useRef<HTMLInputElement>(null)

  const dirty = editing && editContent !== savedContent

  async function loadDir(p: string) {
    setLoading(true); setError(null); setOpenFile(null); setEditing(false)
    try {
      const res = await projectsApi.listFiles(projectId, p)
      setPath(res.path); setEntries(res.entries)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler")
    } finally { setLoading(false) }
  }

  async function openFileEntry(name: string) {
    const filePath = path ? `${path}/${name}` : name
    setLoading(true); setError(null); setEditing(false)
    try {
      const content = await projectsApi.readFile(projectId, filePath)
      setSavedContent(content); setEditContent(content); setOpenFile(name)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler")
    } finally { setLoading(false) }
  }

  async function saveFile() {
    if (!openFile) return
    const filePath = path ? `${path}/${openFile}` : openFile
    setSaving(true); setError(null)
    try {
      await projectsApi.writeFile(projectId, filePath, editContent)
      setSavedContent(editContent); setEditing(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Speichern fehlgeschlagen")
    } finally { setSaving(false) }
  }

  function closeFile() { setOpenFile(null); setEditing(false) }

  async function handleUpload(file: globalThis.File) {
    setUploading(true); setError(null)
    try {
      await projectsApi.uploadFile(projectId, file, path)
      await loadDir(path)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload-Fehler")
    } finally { setUploading(false) }
  }

  async function confirmDelete(name: string) {
    if (!confirm(t("files.delete_confirm", { name }))) return
    setDeleting(name); setError(null)
    try {
      const filePath = path ? `${path}/${name}` : name
      await projectsApi.deleteFile(projectId, filePath)
      await loadDir(path)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lösch-Fehler")
    } finally { setDeleting(null) }
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
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1 text-xs text-zinc-500 flex-1 min-w-0">
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
        <button
          onClick={() => uploadRef.current?.click()}
          disabled={uploading}
          className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-[11px] border border-white/[8%] bg-white/[3%] text-zinc-300 hover:text-zinc-100 hover:bg-white/[6%] disabled:opacity-40"
        >
          {uploading ? <Loader2 size={11} className="animate-spin" /> : <Upload size={11} />}
          {t("files.upload")}
        </button>
        <input
          ref={uploadRef}
          type="file"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) handleUpload(f)
            e.target.value = ""
          }}
        />
      </div>

      {error && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/[6%] px-3 py-2 text-xs text-rose-300">{error}</div>
      )}

      {openFile ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-zinc-400 font-mono truncate">
              {openFile}{dirty && <span className="text-amber-400 ml-1">●</span>}
            </span>
            <div className="flex items-center gap-1">
              {!editing ? (
                <button onClick={() => setEditing(true)}
                  className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-[11px] border border-white/[8%] bg-white/[3%] text-zinc-300 hover:text-zinc-100 hover:bg-white/[6%]">
                  <Pencil size={11} /> {t("files.edit")}
                </button>
              ) : (
                <button onClick={saveFile} disabled={!dirty || saving}
                  className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-[11px] border border-emerald-500/30 bg-emerald-500/15 text-emerald-200 hover:bg-emerald-500/25 disabled:opacity-40 disabled:cursor-not-allowed">
                  {saving ? <Loader2 size={11} className="animate-spin" /> : <Save size={11} />}
                  {t("files.save")}
                </button>
              )}
              <button onClick={closeFile} className="inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] text-zinc-500 hover:text-zinc-200">
                <X size={11} /> {t("files.close")}
              </button>
            </div>
          </div>
          {editing ? (
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              spellCheck={false}
              className="w-full h-[500px] rounded-lg border border-white/[8%] bg-zinc-900 p-3 text-xs text-zinc-200 font-mono resize-none focus:outline-none focus:border-amber-500/40"
            />
          ) : (
            <pre className="rounded-lg border border-white/[8%] bg-zinc-900 p-3 text-xs text-zinc-300 font-mono overflow-auto max-h-[500px] whitespace-pre-wrap break-words">
              {savedContent}
            </pre>
          )}
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
            <div key={e.name} className="group flex items-center gap-2 px-3 py-2 hover:bg-white/[3%] border-b border-white/[4%] last:border-0">
              <button
                onClick={() => e.type === "dir" ? loadDir(path ? `${path}/${e.name}` : e.name) : openFileEntry(e.name)}
                className="flex-1 flex items-center gap-2 text-xs text-left min-w-0"
              >
                {e.type === "dir"
                  ? <Folder size={13} className="text-amber-400 flex-shrink-0" />
                  : <File size={13} className="text-zinc-500 flex-shrink-0" />}
                <span className={`flex-1 truncate ${e.type === "dir" ? "text-zinc-200" : "text-zinc-400"}`}>{e.name}</span>
                {e.size !== null && (
                  <span className="text-zinc-600 flex-shrink-0">{e.size < 1024 ? `${e.size}B` : `${(e.size / 1024).toFixed(1)}KB`}</span>
                )}
              </button>
              {e.type === "file" && (
                <button
                  onClick={() => confirmDelete(e.name)}
                  disabled={deleting === e.name}
                  className="p-1 rounded text-rose-400/0 group-hover:text-rose-400/70 hover:!text-rose-300 hover:bg-rose-500/10 transition-all flex-shrink-0"
                  title={t("files.delete")}
                >
                  {deleting === e.name ? <Loader2 size={11} className="animate-spin" /> : <Trash2 size={11} />}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
