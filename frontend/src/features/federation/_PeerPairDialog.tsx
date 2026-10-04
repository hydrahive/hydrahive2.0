import { useEffect, useState } from "react"
import type { CSSProperties } from "react"
import { useTranslation } from "react-i18next"
import { Copy, X } from "lucide-react"
import { peersApi } from "./api"
import { rgbFor } from "@/shared/colors"

interface Props {
  onClose: () => void
  onAdded: () => void
}

// Schritt 1: eigenen Code erzeugen und an die Gegenseite geben.
// Schritt 2: Code der Gegenseite einfügen → Partner wartet auf Bestätigung.
export function PeerPairDialog({ onClose, onAdded }: Props) {
  const { t } = useTranslation("federation")
  const [name, setName] = useState(window.location.hostname.replace(/[^A-Za-z0-9._-]/g, "-"))
  const [url, setUrl] = useState(`https://${window.location.host}`)
  const [own, setOwn] = useState<{ code: string; fingerprint: string } | null>(null)
  const [foreign, setForeign] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    peersApi.identity().then(i => setOwn(o => o ?? { code: "", fingerprint: i.fingerprint })).catch(() => {})
  }, [])

  async function makeCode() {
    setError("")
    try {
      setOwn(await peersApi.ownCode(name.trim(), url.trim()))
    } catch (e) {
      setError(e instanceof Error ? e.message : t("peers.error"))
    }
  }

  async function addForeign() {
    if (!foreign.trim()) return
    setBusy(true)
    setError("")
    try {
      await peersApi.add(foreign.trim())
      onAdded()
    } catch (e) {
      setError(e instanceof Error ? e.message : t("peers.error"))
    } finally {
      setBusy(false)
    }
  }

  async function copy() {
    if (!own?.code) return
    await navigator.clipboard.writeText(own.code).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const input = "w-full rounded-lg bg-zinc-950/60 border border-white/[8%] px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-violet-500/50"

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="box overflow-hidden w-full max-w-lg p-6 space-y-5" style={{ "--c": rgbFor("/federation") } as CSSProperties}>
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-zinc-100">{t("peers.pair_title")}</h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 transition-colors"><X size={16} /></button>
        </div>

        <section className="space-y-2">
          <p className="text-xs font-medium text-zinc-300">{t("peers.step1")}</p>
          <div className="grid grid-cols-2 gap-2">
            <input className={input} value={name} onChange={e => setName(e.target.value)} placeholder={t("peers.name_ph")} />
            <input className={input} value={url} onChange={e => setUrl(e.target.value)} placeholder="https://100.x.y.z" />
          </div>
          <p className="text-[11px] text-zinc-500">{t("peers.url_hint")}</p>
          <button onClick={makeCode} className="px-3 py-1.5 rounded-lg text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/[6%]">
            {t("peers.make_code")}
          </button>
          {own?.code && (
            <div className="space-y-1">
              <div className="flex gap-2">
                <textarea readOnly value={own.code} rows={3} className={`${input} font-mono text-[11px]`} />
                <button onClick={copy} title={t("peers.copy")} className="self-start p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300">
                  <Copy size={13} />
                </button>
              </div>
              {copied && <p className="text-[11px] text-emerald-400">{t("peers.copied")}</p>}
            </div>
          )}
          {own && (
            <p className="text-[11px] text-zinc-500">
              {t("peers.own_fp")} <code className="text-violet-300">{own.fingerprint}</code>
            </p>
          )}
        </section>

        <section className="space-y-2 border-t border-white/[5%] pt-4">
          <p className="text-xs font-medium text-zinc-300">{t("peers.step2")}</p>
          <textarea
            value={foreign} onChange={e => setForeign(e.target.value)} rows={3}
            placeholder="hhpeer1:…" className={`${input} font-mono text-[11px]`}
          />
          <button
            onClick={addForeign} disabled={busy || !foreign.trim()}
            className="px-3 py-1.5 rounded-lg text-xs bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white"
          >
            {t("peers.add")}
          </button>
        </section>

        {error && <p className="text-xs text-red-400">{error}</p>}
      </div>
    </div>
  )
}
