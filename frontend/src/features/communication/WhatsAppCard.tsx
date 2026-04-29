import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { MessageCircle, Loader2, LinkIcon, Unlink } from "lucide-react"
import { communicationApi, type ChannelStatus } from "./api"
import { WhatsAppFilterPanel } from "./WhatsAppFilterPanel"

const POLL_MS = 1500

export function WhatsAppCard() {
  const { t } = useTranslation("communication")
  const [status, setStatus] = useState<ChannelStatus | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  async function refresh() {
    try {
      setStatus(await communicationApi.whatsapp.status())
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  useEffect(() => {
    refresh()
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  useEffect(() => {
    const polling = status && (status.state === "waiting_qr" || status.state === "connecting")
    if (polling && !pollRef.current) {
      pollRef.current = setInterval(refresh, POLL_MS)
    }
    if (!polling && pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [status?.state])

  async function handleConnect() {
    setBusy(true); setError(null)
    try {
      setStatus(await communicationApi.whatsapp.connect())
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally { setBusy(false) }
  }

  async function handleDisconnect() {
    setBusy(true); setError(null)
    try {
      await communicationApi.whatsapp.disconnect()
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally { setBusy(false) }
  }

  const state = status?.state ?? "disconnected"
  const stateLabel = t(`whatsapp.states.${state}`)
  const isError = state === "error"
  const dotClass = state === "connected"
    ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.7)]"
    : state === "waiting_qr" || state === "connecting"
    ? "bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.7)]"
    : isError ? "bg-rose-400" : "bg-zinc-600"

  return (
    <div className="rounded-xl bg-white/[3%] border border-white/[6%] p-5 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-green-600 flex items-center justify-center shrink-0">
            <MessageCircle className="text-white" size={20} />
          </div>
          <div>
            <h3 className="text-zinc-100 font-semibold">{t("whatsapp.label")}</h3>
            <p className="text-xs text-zinc-500 mt-0.5 max-w-md">{t("whatsapp.description")}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`w-2 h-2 rounded-full ${dotClass}`} />
          <span className="text-xs text-zinc-400">{stateLabel}</span>
        </div>
      </div>

      {status?.detail && state === "connected" && (
        <p className="text-sm text-zinc-300 font-mono">{status.detail}</p>
      )}

      {state === "waiting_qr" && status?.qr_data_url && (
        <div className="flex flex-col items-center gap-3 py-2">
          <img src={status.qr_data_url} alt="WhatsApp QR" className="w-56 h-56 rounded-lg bg-white p-2" />
          <p className="text-xs text-zinc-400 text-center max-w-sm">{t("whatsapp.qr_hint")}</p>
        </div>
      )}

      {isError && status?.detail && (
        <div className="px-3 py-2 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-200 text-xs">
          {t("whatsapp.bridge_error", { detail: status.detail })}
        </div>
      )}

      {error && (
        <div className="px-3 py-2 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-200 text-xs">
          {error}
        </div>
      )}

      <div className="flex justify-end">
        {state === "connected" ? (
          <button onClick={handleDisconnect} disabled={busy}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-200 text-xs font-medium hover:bg-rose-500/25 disabled:opacity-50 transition-colors">
            {busy ? <Loader2 size={12} className="animate-spin" /> : <Unlink size={12} />}
            {t("whatsapp.disconnect")}
          </button>
        ) : (
          <button onClick={handleConnect} disabled={busy || state === "connecting" || state === "waiting_qr"}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-200 text-xs font-medium hover:bg-emerald-500/25 disabled:opacity-50 transition-colors">
            {busy || state === "connecting" || state === "waiting_qr"
              ? <Loader2 size={12} className="animate-spin" />
              : <LinkIcon size={12} />}
            {t("whatsapp.connect")}
          </button>
        )}
      </div>

      {state === "connected" && <WhatsAppFilterPanel />}
    </div>
  )
}
