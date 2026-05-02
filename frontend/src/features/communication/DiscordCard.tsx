import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Bot, Loader2, LinkIcon, Unlink } from "lucide-react"
import { communicationApi, type ChannelStatus } from "./api"
import { DiscordFilterPanel } from "./DiscordFilterPanel"

const POLL_MS = 3000

export function DiscordCard() {
  const { t } = useTranslation("communication")
  const [status, setStatus] = useState<ChannelStatus | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  async function refresh() {
    try {
      setStatus(await communicationApi.discord.status())
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  useEffect(() => {
    refresh()
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  useEffect(() => {
    const polling = status && (status.state === "connecting" || status.state === "waiting_qr")
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
      setStatus(await communicationApi.discord.connect())
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally { setBusy(false) }
  }

  async function handleDisconnect() {
    setBusy(true); setError(null)
    try {
      await communicationApi.discord.disconnect()
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally { setBusy(false) }
  }

  const state = status?.state ?? "disconnected"
  const stateLabel = t(`discord.states.${state}`)
  const isConnected = state === "connected"
  const isConnecting = state === "connecting" || state === "waiting_qr"
  const isError = state === "error"

  const dotClass = isConnected
    ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.7)]"
    : isConnecting
    ? "bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.7)]"
    : isError ? "bg-rose-400" : "bg-zinc-600"

  return (
    <div className="rounded-xl bg-white/[3%] border border-white/[6%] p-5 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shrink-0">
            <Bot className="text-white" size={20} />
          </div>
          <div>
            <h3 className="text-zinc-100 font-semibold">{t("discord.label")}</h3>
            <p className="text-xs text-zinc-500 mt-0.5 max-w-md">{t("discord.description")}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`w-2 h-2 rounded-full ${dotClass}`} />
          <span className="text-xs text-zinc-400">{stateLabel}</span>
        </div>
      </div>

      {isError && status?.detail && (
        <div className="px-3 py-2 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-200 text-xs">
          {status.detail}
        </div>
      )}

      {error && (
        <div className="px-3 py-2 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-200 text-xs">
          {error}
        </div>
      )}

      <div className="flex justify-end">
        {isConnected ? (
          <button onClick={handleDisconnect} disabled={busy}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-200 text-xs font-medium hover:bg-rose-500/25 disabled:opacity-50 transition-colors">
            {busy ? <Loader2 size={12} className="animate-spin" /> : <Unlink size={12} />}
            {t("discord.disconnect")}
          </button>
        ) : (
          <button onClick={handleConnect} disabled={busy || isConnecting}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-500/15 border border-indigo-500/30 text-indigo-200 text-xs font-medium hover:bg-indigo-500/25 disabled:opacity-50 transition-colors">
            {busy || isConnecting
              ? <Loader2 size={12} className="animate-spin" />
              : <LinkIcon size={12} />}
            {t("discord.connect")}
          </button>
        )}
      </div>

      <DiscordFilterPanel />
    </div>
  )
}
