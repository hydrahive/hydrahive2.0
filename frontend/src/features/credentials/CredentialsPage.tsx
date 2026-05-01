import { useEffect, useState } from "react"
import { Key, Loader2, Plus } from "lucide-react"
import { useTranslation } from "react-i18next"
import { credentialsApi } from "./api"
import { CredentialEditor } from "./CredentialEditor"
import type { Credential } from "./types"

export function CredentialsPage() {
  const { t } = useTranslation("credentials")
  const [creds, setCreds] = useState<Credential[]>([])
  const [loading, setLoading] = useState(true)
  const [editor, setEditor] = useState<Credential | "new" | null>(null)

  async function reload() {
    setLoading(true)
    try { setCreds(await credentialsApi.list()) }
    catch { setCreds([]) }
    finally { setLoading(false) }
  }

  useEffect(() => { reload() }, [])

  return (
    <div className="space-y-5 max-w-4xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">{t("title")}</h1>
          <p className="text-zinc-500 text-sm mt-0.5">{t("subtitle")}</p>
        </div>
        <button onClick={() => setEditor("new")}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-medium">
          <Plus size={12} /> {t("new")}
        </button>
      </div>

      <p className="text-[11px] text-zinc-500 bg-amber-500/[5%] border border-amber-500/15 rounded-md px-3 py-2">
        {t("security_note")}
      </p>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={20} className="animate-spin text-zinc-500" />
        </div>
      ) : creds.length === 0 ? (
        <p className="text-xs text-zinc-600 text-center py-8">{t("empty")}</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {creds.map((c) => (
            <button key={c.name} onClick={() => setEditor(c)}
              className="text-left rounded-lg border border-white/[8%] bg-white/[2%] p-3 hover:border-white/[15%] hover:bg-white/[5%] transition-colors">
              <div className="flex items-center gap-2 mb-1">
                <Key size={11} className="text-amber-300 flex-shrink-0" />
                <p className="text-sm font-mono text-zinc-200 truncate flex-1">{c.name}</p>
                <span className="px-1.5 py-0.5 rounded-full bg-violet-500/[8%] border border-violet-500/20 text-[10px] text-violet-300 flex-shrink-0">
                  {t(`type_${c.type}`)}
                </span>
              </div>
              {c.description && <p className="text-xs text-zinc-400 line-clamp-1">{c.description}</p>}
              <p className="text-[10px] text-zinc-600 font-mono truncate mt-1">{c.url_pattern}</p>
            </button>
          ))}
        </div>
      )}

      {editor && (
        <CredentialEditor
          credential={editor === "new" ? null : editor}
          onClose={() => setEditor(null)}
          onSaved={async () => { setEditor(null); await reload() }}
          onDeleted={async () => { setEditor(null); await reload() }}
        />
      )}
    </div>
  )
}
