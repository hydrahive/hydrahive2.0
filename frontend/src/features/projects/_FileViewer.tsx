import { lazy, Suspense, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Loader2, Pencil, Save, X } from "lucide-react"

const MonacoEditor = lazy(() => import("@monaco-editor/react").then((m) => ({ default: m.default })))

interface Props {
  filename: string
  initialContent: string
  onClose: () => void
  onSave: (content: string) => Promise<void>
}

const EXT_TO_LANG: Record<string, string> = {
  py: "python", js: "javascript", ts: "typescript", tsx: "typescript", jsx: "javascript",
  json: "json", yaml: "yaml", yml: "yaml", md: "markdown", html: "html", css: "css",
  scss: "scss", sh: "shell", bash: "shell", sql: "sql", rs: "rust", go: "go",
  java: "java", c: "c", cpp: "cpp", h: "cpp", rb: "ruby", php: "php",
  toml: "ini", ini: "ini", cfg: "ini", xml: "xml", dockerfile: "dockerfile",
}

function detectLanguage(filename: string): string {
  if (filename === "Dockerfile") return "dockerfile"
  if (filename === "Makefile") return "makefile"
  const ext = filename.split(".").pop()?.toLowerCase() ?? ""
  return EXT_TO_LANG[ext] ?? "plaintext"
}

export function FileViewer({ filename, initialContent, onClose, onSave }: Props) {
  const { t } = useTranslation("projects")
  const [editing, setEditing] = useState(false)
  const [content, setContent] = useState(initialContent)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const dirty = content !== initialContent

  useEffect(() => { setContent(initialContent); setEditing(false); setError(null) }, [initialContent, filename])

  async function save() {
    setSaving(true); setError(null)
    try {
      await onSave(content)
      setEditing(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler")
    } finally { setSaving(false) }
  }

  const language = detectLanguage(filename)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-zinc-400 font-mono truncate">{filename}{dirty && <span className="text-amber-400 ml-1">●</span>}</span>
        <div className="flex items-center gap-1">
          {!editing ? (
            <button onClick={() => setEditing(true)}
              className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-[11px] border border-white/[8%] bg-white/[3%] text-zinc-300 hover:text-zinc-100 hover:bg-white/[6%]">
              <Pencil size={11} /> {t("files.edit")}
            </button>
          ) : (
            <button onClick={save} disabled={!dirty || saving}
              className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-[11px] border border-emerald-500/30 bg-emerald-500/15 text-emerald-200 hover:bg-emerald-500/25 disabled:opacity-40 disabled:cursor-not-allowed">
              {saving ? <Loader2 size={11} className="animate-spin" /> : <Save size={11} />}
              {t("files.save")}
            </button>
          )}
          <button onClick={onClose} className="inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] text-zinc-500 hover:text-zinc-200">
            <X size={11} /> {t("files.close")}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/[6%] px-3 py-2 text-xs text-rose-300">{error}</div>
      )}

      <div className="rounded-lg border border-white/[8%] overflow-hidden h-[500px]">
        <Suspense fallback={
          <div className="h-full flex items-center justify-center text-xs text-zinc-500 gap-2">
            <Loader2 size={13} className="animate-spin" /> Editor wird geladen…
          </div>
        }>
          <MonacoEditor
            height="500px"
            language={language}
            value={content}
            theme="vs-dark"
            onChange={(v) => setContent(v ?? "")}
            options={{
              readOnly: !editing,
              minimap: { enabled: false },
              fontSize: 12,
              lineNumbers: "on",
              scrollBeyondLastLine: false,
              wordWrap: "on",
              automaticLayout: true,
            }}
          />
        </Suspense>
      </div>
    </div>
  )
}
