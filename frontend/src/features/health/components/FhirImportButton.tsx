import { useState, useRef } from "react"
import { Upload } from "lucide-react"
import { fhirApi } from "../api"

interface Props {
  onImported?: (result: { imported: number; updated: number }) => void
}

export function FhirImportButton({ onImported }: Props) {
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = async (file: File) => {
    setLoading(true)
    setMessage(null)
    try {
      const result = file.name.endsWith(".zip")
        ? await fhirApi.importEgaZip(file)
        : await fhirApi.importBundle(file)
      setMessage(`${result.imported} importiert, ${result.updated} aktualisiert`)
      onImported?.(result)
    } catch {
      setMessage("Fehler beim Import")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center gap-3">
      <input
        ref={inputRef}
        type="file"
        accept=".json,.zip"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
      <button
        onClick={() => inputRef.current?.click()}
        disabled={loading}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm bg-rose-500/10 text-rose-300 border border-rose-500/20 hover:bg-rose-500/20 transition-colors disabled:opacity-50"
      >
        <Upload size={14} />
        {loading ? "Importiere…" : "Akte aktualisieren"}
      </button>
      {message && <span className="text-xs text-zinc-400">{message}</span>}
    </div>
  )
}
