import { lazy, Suspense, useState, useEffect } from "react"
import { useTranslation } from "react-i18next"
import { Save } from "lucide-react"
import type { FileContent } from "./api"

// Setup (lokaler Loader + Worker) zuerst, dann den Editor — beides im Lazy-Chunk.
const Monaco = lazy(async () => {
  await import("./monacoSetup")
  return import("@monaco-editor/react")
})

function langFromPath(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase()
  const map: Record<string, string> = {
    ts: "typescript", tsx: "typescript", js: "javascript", jsx: "javascript",
    py: "python", json: "json", md: "markdown", css: "css", html: "html",
    sh: "shell", yml: "yaml", yaml: "yaml", toml: "ini", rs: "rust", go: "go",
    sql: "sql", dockerfile: "dockerfile", xml: "xml",
  }
  return map[ext ?? ""] ?? "plaintext"
}

interface Props { file: FileContent; onSave: (content: string) => Promise<void> }

export function FileEditor({ file, onSave }: Props) {
  const { t } = useTranslation("workspace")
  const [value, setValue] = useState(file.content)
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => { setValue(file.content); setDirty(false) }, [file.path, file.content])

  async function save() {
    setSaving(true)
    try { await onSave(value); setDirty(false) } finally { setSaving(false) }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-2 py-1 border-b border-white/[6%]">
        <span className="text-[10px] text-zinc-400 truncate flex-1 font-mono">{file.path}{dirty ? " •" : ""}</span>
        <button onClick={save} disabled={!dirty || saving}
          className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] bg-violet-500/15 text-violet-300 disabled:opacity-40">
          <Save size={10} /> {t("save")}
        </button>
      </div>
      <div className="flex-1 min-h-0">
        <Suspense fallback={<div className="p-2 text-[11px] text-zinc-600">{t("loading")}</div>}>
          <Monaco
            height="100%" theme="vs-dark" language={langFromPath(file.path)} value={value}
            onChange={(v) => { setValue(v ?? ""); setDirty(true) }}
            options={{ fontSize: 13, minimap: { enabled: false }, scrollBeyondLastLine: false, wordWrap: "on" }}
          />
        </Suspense>
      </div>
    </div>
  )
}
