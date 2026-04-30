import { useEffect, useRef, useState } from "react"
import { X } from "lucide-react"
import { Terminal } from "xterm"
import { FitAddon } from "xterm-addon-fit"
import "xterm/css/xterm.css"
import { useAuthStore } from "@/features/auth/useAuthStore"
import type { Container } from "./types"

interface Props {
  container: Container
  onClose: () => void
}

export function ContainerConsoleModal({ container, onClose }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const termRef = useRef<Terminal | null>(null)
  const fitRef = useRef<FitAddon | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const [status, setStatus] = useState<"connecting" | "connected" | "closed">("connecting")
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!containerRef.current) return
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
    term.open(containerRef.current)
    fit.fit()
    termRef.current = term
    fitRef.current = fit

    const proto = window.location.protocol === "https:" ? "wss:" : "ws:"
    const url = `${proto}//${window.location.host}/api/containers/${container.container_id}/console?token=${encodeURIComponent(token)}`
    const ws = new WebSocket(url)
    ws.binaryType = "arraybuffer"
    wsRef.current = ws

    ws.onopen = () => {
      setStatus("connected")
      const { rows, cols } = term
      ws.send(JSON.stringify({ type: "resize", rows, cols }))
    }
    ws.onmessage = (ev) => {
      if (ev.data instanceof ArrayBuffer) {
        term.write(new Uint8Array(ev.data))
      } else if (typeof ev.data === "string") {
        term.write(ev.data)
      }
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
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "input", data }))
      }
    })

    const onResize = () => {
      try { fit.fit() } catch { /* */ }
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "resize", rows: term.rows, cols: term.cols }))
      }
    }
    window.addEventListener("resize", onResize)

    term.focus()

    return () => {
      window.removeEventListener("resize", onResize)
      onData.dispose()
      try { ws.close() } catch { /* */ }
      term.dispose()
    }
  }, [container.container_id])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="w-full max-w-5xl rounded-xl border border-white/[10%] bg-zinc-950 shadow-2xl flex flex-col"
        style={{ height: "min(80vh, 700px)" }}>
        <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-white/[8%]">
          <div className="flex items-center gap-2 min-w-0">
            <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
              status === "connected" ? "bg-emerald-400" : status === "connecting" ? "bg-amber-400 animate-pulse" : "bg-rose-400"
            }`} />
            <p className="text-sm font-mono text-zinc-200 truncate">{container.name}</p>
            <span className="text-[11px] text-zinc-500">— Console</span>
          </div>
          <button onClick={onClose}
            className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-200 hover:bg-white/[5%]">
            <X size={16} />
          </button>
        </div>

        {error && (
          <div className="px-4 py-2 bg-rose-500/10 border-b border-rose-500/30 text-xs text-rose-200">{error}</div>
        )}

        <div ref={containerRef} className="flex-1 min-h-0 p-2 bg-[#0b0b0f]" />

        <div className="px-4 py-2 border-t border-white/[8%] text-[11px] text-zinc-500 font-mono">
          incus exec — Strg+D zum Beenden
        </div>
      </div>
    </div>
  )
}
