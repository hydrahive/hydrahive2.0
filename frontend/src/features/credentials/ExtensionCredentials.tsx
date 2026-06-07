import type { CSSProperties } from "react"
import { useTranslation } from "react-i18next"
import { useEffect, useState } from "react"
import { Eye, EyeOff, Package, RefreshCw } from "lucide-react"
import { rgbFor } from "@/shared/colors"
import { api } from "@/shared/api-client"

interface CredField {
  key: string
  label: string
  value: string
  secret: boolean
}

interface ExtCred {
  extension_id: string
  extension_name: string
  fields: CredField[]
}

function resolveUrl(value: string): string {
  if (value.startsWith(":") || (value.startsWith("/") && !value.startsWith("//")))
    return `http://${window.location.hostname}${value}`
  return value
}

function FieldRow({ field }: { field: CredField }) {
  const [visible, setVisible] = useState(false)
  const display = field.secret && !visible ? "•".repeat(Math.min(field.value.length, 24)) : field.value
  const fullUrl = !field.secret && field.key === "url" ? resolveUrl(field.value) : null
  return (
    <div className="flex items-center justify-between gap-3 py-1.5 border-b border-white/[4%] last:border-0">
      <span className="text-xs text-zinc-500 shrink-0 w-32">{field.label}</span>
      <span className="flex-1 font-mono text-xs text-zinc-200 truncate">
        {fullUrl ? (
          <a href={fullUrl} target="_blank" rel="noreferrer"
            className="text-violet-400 hover:text-violet-300 transition-colors">
            {fullUrl}
          </a>
        ) : display}
      </span>
      {field.secret && (
        <button onClick={() => setVisible((v) => !v)}
          className="shrink-0 p-1 rounded text-zinc-600 hover:text-zinc-300 transition-colors">
          {visible ? <EyeOff size={12} /> : <Eye size={12} />}
        </button>
      )}
    </div>
  )
}

export function ExtensionCredentials() {
  const { t } = useTranslation("credentials")
  const [creds, setCreds] = useState<ExtCred[]>([])
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    try { setCreds(await api.get<ExtCred[]>("/admin/extensions/credentials")) }
    catch { setCreds([]) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-zinc-500">
          Zugangsdaten die bei der Extension-Installation automatisch generiert wurden.
        </p>
        <button onClick={load}
          className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-white/[5%] transition-colors">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {loading ? (
        <p className="text-xs text-zinc-600 py-6 text-center">{t("loading")}</p>
      ) : creds.length === 0 ? (
        <div className="text-center py-10">
          <Package size={24} className="mx-auto text-zinc-700 mb-2" />
          <p className="text-xs text-zinc-600">{t("extension_empty")}</p>
          <p className="text-[11px] text-zinc-700 mt-1">
            Werden automatisch beim Installieren von Extensions gespeichert.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {creds.map((c) => (
            <div key={c.extension_id}
              className="box overflow-hidden p-4" style={{ "--c": rgbFor("/credentials") } as CSSProperties}>
              <div className="flex items-center gap-2 mb-3">
                <Package size={13} className="text-violet-400 shrink-0" />
                <span className="text-sm font-medium text-zinc-100">{c.extension_name}</span>
              </div>
              <div>
                {c.fields.map((f) => <FieldRow key={f.label} field={f} />)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
