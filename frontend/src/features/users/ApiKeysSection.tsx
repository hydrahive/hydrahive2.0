import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Copy, KeyRound, Plus, Trash2 } from "lucide-react"
import { apiKeysApi } from "./api"
import type { ApiKey } from "./types"

export function ApiKeysSection() {
  const { t } = useTranslation("users")
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [newName, setNewName] = useState("")
  const [creating, setCreating] = useState(false)
  const [newKey, setNewKey] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  async function load() {
    try { setKeys(await apiKeysApi.list()) } catch { /* leise */ }
  }

  useEffect(() => { load() }, [])

  async function handleCreate() {
    if (!newName.trim()) return
    setCreating(true)
    try {
      const res = await apiKeysApi.create(newName.trim())
      setNewKey(res.key)
      setNewName("")
      await load()
    } catch { /* leise */ }
    finally { setCreating(false) }
  }

  async function handleDelete(id: string) {
    if (!confirm(t("apikeys.delete_confirm"))) return
    try {
      await apiKeysApi.delete(id)
      await load()
    } catch { /* leise */ }
  }

  function handleCopy() {
    if (!newKey) return
    navigator.clipboard.writeText(newKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
          <KeyRound size={15} className="text-amber-400" />
          {t("apikeys.title")}
        </h2>
        <p className="text-xs text-zinc-500 mt-0.5">{t("apikeys.subtitle")}</p>
      </div>

      {newKey && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 space-y-2">
          <p className="text-xs text-amber-300 font-medium">{t("apikeys.save_now")}</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 text-xs font-mono text-zinc-200 bg-black/30 rounded px-2 py-1.5 break-all">
              {newKey}
            </code>
            <button
              onClick={handleCopy}
              className="shrink-0 p-1.5 rounded hover:bg-white/10 text-zinc-400 hover:text-zinc-200 transition-colors"
              title={t("apikeys.copy")}
            >
              <Copy size={14} />
            </button>
          </div>
          {copied && <p className="text-xs text-emerald-400">{t("apikeys.copied")}</p>}
          <button
            onClick={() => setNewKey(null)}
            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            {t("apikeys.dismiss")}
          </button>
        </div>
      )}

      <div className="flex gap-2">
        <input
          type="text"
          value={newName}
          onChange={e => setNewName(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleCreate()}
          placeholder={t("apikeys.name_placeholder")}
          className="flex-1 bg-white/[4%] border border-white/[8%] rounded-lg px-3 py-2 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-amber-500/40"
        />
        <button
          onClick={handleCreate}
          disabled={creating || !newName.trim()}
          className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 hover:bg-amber-500/20 text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Plus size={14} /> {t("apikeys.create")}
        </button>
      </div>

      {keys.length > 0 && (
        <div className="space-y-1.5">
          {keys.map(k => (
            <div key={k.id} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/[2%] border border-white/[5%]">
              <KeyRound size={13} className="text-zinc-600 shrink-0" />
              <div className="flex-1 min-w-0">
                <span className="text-sm text-zinc-300">{k.name}</span>
                <span className="ml-2 text-xs text-zinc-600">{k.username}</span>
              </div>
              <span className="text-xs text-zinc-600 shrink-0">
                {new Date(k.created_at).toLocaleDateString()}
              </span>
              <button
                onClick={() => handleDelete(k.id)}
                className="shrink-0 p-1 rounded hover:bg-white/10 text-zinc-600 hover:text-red-400 transition-colors"
              >
                <Trash2 size={13} />
              </button>
            </div>
          ))}
        </div>
      )}

      {keys.length === 0 && !newKey && (
        <p className="text-xs text-zinc-600 italic">{t("apikeys.empty")}</p>
      )}
    </div>
  )
}
