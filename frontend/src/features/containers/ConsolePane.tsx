import { useEffect, useRef, useState } from "react"
import { Terminal } from "xterm"
import { FitAddon } from "xterm-addon-fit"
import "xterm/css/xterm.css"
import { useAuthStore } from "@/features/auth/useAuthStore"

interface Props {
  containerId: string
  className?: string
}

export type ConsoleStatus = "connecting" | "connected" | "closed"

export function ConsolePane({ containerId, className }: Props) {
  const wrapRef = useRef<HTMLDivElement | null>(null)
  const [status, setStatus] = useState<ConsoleStatus>("connecting")
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!wrapRef.current) return
    const token = useAuthStore.getState().token
    if (!token) {
      setError("Nicht angemeldet")
      setStatus("closed")
      return
    }

    const term = new Terminal({
      cursorBlink: true,
      fontFamily: '"JetBrains Mono", "Fira Code", Menlo, Consolas, monospace',
      fontSize: 13,
      theme: { background: "#0b0b0f", foreground: "#e4e4e7", cursor: "#a78bfa" },
      convertEol: true,
    })
    const fit = new FitAddon()
    term.loadAddon(fit)
    term.open(wrapRef.current)
    fit.fit()

    const proto = window.location.protocol === "https:" ? "wss:" : "ws:"
    const url = `${proto}//${window.location.host}/api/containers/${containerId}/console?token=${encodeURIComponent(token)}`
    const ws = new WebSocket(url)
    ws.binaryType = "arraybuffer"

    ws.onopen = () => {
      setStatus("connected")
      ws.send(JSON.stringify({ type: "resize", rows: term.rows, cols: term.cols }))
    }
    ws.onmessage = (ev) => {
      if (ev.data instanceof ArrayBuffer) term.write(new Uint8Array(ev.data))
      else if (typeof ev.data === "string") term.write(ev.data)
    }
    ws.onerror = () => setError("Verbindung fehlgeschlagen")
    ws.onclose = (ev) => {
      setStatus("closed")
      if (ev.code === 4401) setError("Nicht autorisiert")
      else if (ev.code === 4404) setError("Container nicht gefunden")
      else if (ev.code === 4409) setError("Container läuft nicht")
      else if (ev.code === 4500) setError("Backend-Fehler")
    }

    const onData = term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "input", data }))
    })

    const onResize = () => {
      try { fit.fit() } catch { /* */ }
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "resize", rows: term.rows, cols: term.cols }))
      }
    }
    window.addEventListener("resize", onResize)
    const ro = new ResizeObserver(onResize)
    if (wrapRef.current) ro.observe(wrapRef.current)

    term.focus()

    return () => {
      window.removeEventListener("resize", onResize)
      ro.disconnect()
      onData.dispose()
      try { ws.close() } catch { /* */ }
      term.dispose()
    }
  }, [containerId])

  return (
    <div className={`flex flex-col min-h-0 ${className ?? ""}`}>
      {error && (
        <div className="px-4 py-2 bg-rose-500/10 border-b border-rose-500/30 text-xs text-rose-200 flex-shrink-0">{error}</div>
      )}
      <div className="flex-1 min-h-0 p-2 bg-[#0b0b0f]" ref={wrapRef} />
      <div className="px-4 py-2 border-t border-white/[8%] text-[11px] text-zinc-500 font-mono flex items-center justify-between flex-shrink-0">
        <span>incus exec — Strg+D zum Beenden</span>
        <span className={
          status === "connected" ? "text-emerald-400" :
          status === "connecting" ? "text-amber-400" : "text-rose-400"
        }>● {status}</span>
      </div>
    </div>
  )
}
