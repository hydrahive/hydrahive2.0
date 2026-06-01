import { useTranslation } from "react-i18next"
import { useState, useRef } from "react"
import { Upload } from "lucide-react"
import { egaApi } from "../api"

interface Props {
  onImported?: () => void
}

export function EgaImportButton({ onImported }: Props) {
  const { t } = useTranslation("health")
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = async (file: File) => {
    setLoading(true)
    setMessage(null)
    try {
      const result = await egaApi.importZip(file)
      setMessage(`${result.imported} neu, ${result.updated} aktualisiert`)
      onImported?.()
    } catch {
      setMessage(t("import.failed"))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center gap-3">
      <input
        ref={inputRef}
        type="file"
        accept=".zip"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
      <button
        onClick={() => inputRef.current?.click()}
        disabled={loading}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm bg-rose-500/10 text-rose-300 border border-rose-500/20 hover:bg-rose-500/20 transition-colors disabled:opacity-50"
      >
        <Upload size={14} />
        {loading ? t("import.importing") : t("import.update_akte")}
      </button>
      {message && <span className="text-xs text-zinc-400">{message}</span>}
    </div>
  )
}
