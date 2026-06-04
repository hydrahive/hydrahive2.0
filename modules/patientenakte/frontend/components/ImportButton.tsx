import { useState, useRef } from "react"
import { useTranslation } from "react-i18next"
import { Upload } from "lucide-react"

interface Props {
  label: string
  accept: string
  onImport: (file: File) => Promise<{ imported: number; updated: number }>
  onDone?: () => void
}

export function ImportButton({ label, accept, onImport, onDone }: Props) {
  const { t } = useTranslation("akte")
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = async (file: File) => {
    setLoading(true)
    setMessage(null)
    try {
      const r = await onImport(file)
      setMessage(t("import.result", { imported: r.imported, updated: r.updated }))
      onDone?.()
    } catch {
      setMessage(t("import.failed"))
    } finally {
      setLoading(false)
      if (inputRef.current) inputRef.current.value = ""
    }
  }

  return (
    <div className="flex items-center gap-2">
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
      <button
        onClick={() => inputRef.current?.click()}
        disabled={loading}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm bg-rose-500/10 text-rose-300 border border-rose-500/20 hover:bg-rose-500/20 transition-colors disabled:opacity-50 whitespace-nowrap"
      >
        <Upload size={14} />
        {loading ? t("import.importing") : label}
      </button>
      {message && <span className="text-xs text-zinc-400">{message}</span>}
    </div>
  )
}
