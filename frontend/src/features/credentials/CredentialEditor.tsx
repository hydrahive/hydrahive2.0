import { useEffect, useState } from "react"
import { Eye, EyeOff, Loader2, Save, Trash2, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { credentialsApi } from "./api"
import type { Credential, CredentialType } from "./types"

interface Props {
  credential: Credential | null  // null = neu
  onClose: () => void
  onSaved: () => void
  onDeleted?: () => void
}

const NAME_RE = /^[a-z0-9][a-z0-9_-]{0,49}$/
const TYPES: CredentialType[] = ["bearer", "basic", "cookie", "header", "query"]

export function CredentialEditor({ credential, onClose, onSaved, onDeleted }: Props) {
  const { t } = useTranslation("credentials")
  const { t: tCommon } = useTranslation("common")
  const isNew = !credential
  const [name, setName] = useState(credential?.name ?? "")
  const [type, setType] = useState<CredentialType>(credential?.type ?? "bearer")
  const [value, setValue] = useState("")
  const [showValue, setShowValue] = useState(false)
  const [urlPattern, setUrlPattern] = useState(credential?.url_pattern ?? "*")
  const [description, setDescription] = useState(credential?.description ?? "")
  const [headerName, setHeaderName] = useState(credential?.header_name ?? "")
  const [queryParam, setQueryParam] = useState(credential?.query_param ?? "")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Bei Edit: Token nachladen on demand wenn User es enthüllt
    if (credential && !showValue) return
    if (credential && showValue && !value) {
      credentialsApi.get(credential.name, true)
        .then((c) => setValue(c.value))
        .catch(() => {})
    }
  }, [credential, showValue])

  const validName = NAME_RE.test(name)
  const needsHeader = type === "header"
  const needsQuery = type === "query"

  async function save() {
    if (!validName) { setError(t("name_invalid")); return }
    if (needsHeader && !headerName) { setError(t("header_name_required")); return }
    if (needsQuery && !queryParam) { setError(t("query_param_required")); return }
    setBusy(true); setError(null)
    try {
      await credentialsApi.save({
        name, type, value, url_pattern: urlPattern || "*",
        description, header_name: headerName, query_param: queryParam,
      })
      onSaved()
    } catch (e) {
      setError(e instanceof Error ? e.message : tCommon("status.error"))
    } finally { setBusy(false) }
  }

  async function remove() {
    if (!credential) return
    if (!confirm(t("delete_confirm", { name: credential.name }))) return
    setBusy(true); setError(null)
    try { await credentialsApi.remove(credential.name); onDeleted?.() }
    catch (e) { setError(e instanceof Error ? e.message : tCommon("status.error")) }
    finally { setBusy(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg rounded-2xl border border-white/[8%] bg-zinc-900 p-5 shadow-2xl shadow-black/40 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">
            {isNew ? t("new_title") : t("edit_title", { name: credential!.name })}
          </h2>
          <button onClick={onClose} className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
            <X size={16} />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <Field label={t("name")}>
            <input value={name} onChange={(e) => setName(e.target.value)} disabled={!isNew}
              placeholder="forum_metin"
              className={`w-full px-2 py-1 rounded-md bg-zinc-950 border text-xs text-zinc-200 font-mono ${
                name && !validName ? "border-rose-500/40" : "border-white/[8%]"
              } disabled:opacity-50`} />
          </Field>
          <Field label={t("type")}>
            <select value={type} onChange={(e) => setType(e.target.value as CredentialType)}
              className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200">
              {TYPES.map((tp) => <option key={tp} value={tp}>{t(`type_${tp}`)}</option>)}
            </select>
          </Field>
        </div>

        <Field label={t("value")} hint={t(`value_hint_${type}`)}>
          <div className="flex gap-1">
            <input type={showValue ? "text" : "password"} value={value} onChange={(e) => setValue(e.target.value)}
              placeholder={credential?.value_set ? "••••••••" : ""}
              className="flex-1 px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 font-mono" />
            <button type="button" onClick={() => setShowValue(!showValue)}
              className="px-2 py-1 rounded-md text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
              {showValue ? <EyeOff size={11} /> : <Eye size={11} />}
            </button>
          </div>
        </Field>

        {needsHeader && (
          <Field label={t("header_name")}>
            <input value={headerName} onChange={(e) => setHeaderName(e.target.value)}
              placeholder="X-Api-Key"
              className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 font-mono" />
          </Field>
        )}
        {needsQuery && (
          <Field label={t("query_param")}>
            <input value={queryParam} onChange={(e) => setQueryParam(e.target.value)}
              placeholder="api_key"
              className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 font-mono" />
          </Field>
        )}

        <Field label={t("url_pattern")} hint={t("url_pattern_hint")}>
          <input value={urlPattern} onChange={(e) => setUrlPattern(e.target.value)}
            placeholder="https://forum.metin2.de/*"
            className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 font-mono" />
        </Field>

        <Field label={t("description")}>
          <input value={description} onChange={(e) => setDescription(e.target.value)}
            className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200" />
        </Field>

        {error && (
          <p className="text-xs text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-lg px-3 py-2">{error}</p>
        )}

        <div className="flex justify-between gap-2 pt-1">
          {!isNew && onDeleted && (
            <button onClick={remove} disabled={busy}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs text-rose-300 hover:bg-rose-500/10 border border-rose-500/30 disabled:opacity-30">
              <Trash2 size={11} /> {tCommon("actions.delete")}
            </button>
          )}
          <div className="flex-1" />
          <button onClick={onClose}
            className="px-3 py-1.5 rounded-md text-xs text-zinc-400 hover:text-zinc-200 hover:bg-white/5">
            {tCommon("actions.cancel")}
          </button>
          <button onClick={save} disabled={!validName || busy}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-md bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-medium disabled:opacity-30">
            {busy ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
            {tCommon("actions.save")}
          </button>
        </div>
      </div>
    </div>
  )
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-0.5">
      <label className="block text-[10px] font-medium text-zinc-500">{label}</label>
      {children}
      {hint && <p className="text-[10px] text-zinc-600 mt-0.5">{hint}</p>}
    </div>
  )
}
