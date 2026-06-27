import { useState } from "react"
import { Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { projectsApi } from "./api"
import type { SmbMount } from "./types"

interface Props {
  onCreated: (m: SmbMount) => Promise<void>
}

/** Legt einen neuen SMB-Mount an (host/share/credential). Danach muss er noch
 *  zugewiesen werden — onCreated reloadet die Available-Liste. */
export function CreateMountForm({ onCreated }: Props) {
  const { t } = useTranslation("projects")
  const { t: tCommon } = useTranslation("common")
  const [name, setName] = useState("")
  const [host, setHost] = useState("")
  const [share, setShare] = useState("")
  const [subpath, setSubpath] = useState("")
  const [credential, setCredential] = useState("")
  const [readOnly, setReadOnly] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = name.trim() && host.trim() && share.trim() && !busy

  async function submit() {
    setBusy(true); setError(null)
    try {
      const m = await projectsApi.createMount({
        name: name.trim(), host: host.trim(), share: share.trim(),
        subpath: subpath.trim() || null,
        credential: credential.trim() || null,
        read_only: readOnly,
      })
      setName(""); setHost(""); setShare(""); setSubpath(""); setCredential(""); setReadOnly(false)
      await onCreated(m)
    } catch (e) {
      setError(e instanceof Error ? e.message : tCommon("status.error"))
    } finally { setBusy(false) }
  }

  const inputCls = "w-full px-2 py-1.5 rounded-md bg-zinc-900 border border-white/[8%] text-xs text-zinc-200 placeholder:text-zinc-600 focus:border-violet-500/50 outline-none"

  return (
    <div className="space-y-2 pt-2 border-t border-white/[6%]">
      <p className="text-[11px] text-violet-300 font-medium">{t("mounts.create_title")}</p>
      {error && (
        <p className="text-xs text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-lg px-2 py-1">{error}</p>
      )}
      <div className="grid grid-cols-2 gap-2">
        <input className={inputCls} placeholder={t("mounts.f_name")} value={name} onChange={(e) => setName(e.target.value)} />
        <input className={inputCls} placeholder={t("mounts.f_host")} value={host} onChange={(e) => setHost(e.target.value)} />
        <input className={inputCls} placeholder={t("mounts.f_share")} value={share} onChange={(e) => setShare(e.target.value)} />
        <input className={inputCls} placeholder={t("mounts.f_subpath")} value={subpath} onChange={(e) => setSubpath(e.target.value)} />
        <input className={inputCls} placeholder={t("mounts.f_credential")} value={credential} onChange={(e) => setCredential(e.target.value)} />
        <label className="flex items-center gap-2 text-xs text-zinc-400 px-1">
          <input type="checkbox" checked={readOnly} onChange={(e) => setReadOnly(e.target.checked)} className="accent-violet-500" />
          {t("mounts.f_readonly")}
        </label>
      </div>
      <p className="text-[10px] text-zinc-600">{t("mounts.credential_hint")}</p>
      <button onClick={submit} disabled={!canSubmit}
        className="flex items-center gap-1 px-3 py-1.5 rounded-md bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-medium disabled:opacity-40">
        {busy && <Loader2 size={11} className="animate-spin" />}
        {t("mounts.create_submit")}
      </button>
    </div>
  )
}
