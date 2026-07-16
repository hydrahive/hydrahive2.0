import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Terminal } from "xterm"
import { FitAddon } from "xterm-addon-fit"
import "xterm/css/xterm.css"
import { AdminFeedback, AdminStatus, type AdminStatusTone } from "@/features/cockpit/admin/ui"
import { useAuthStore } from "@/features/auth/useAuthStore"

interface Props {
  containerId: string
  className?: string
}

export type ConsoleStatus = "connecting" | "connected" | "closed"

const STATUS_TONES: Record<ConsoleStatus, AdminStatusTone> = {
  connecting: "warning",
  connected: "success",
  closed: "danger",
}

export function ConsolePane({ containerId, className }: Props) {
  const { t } = useTranslation("containers")
  const wrapRef = useRef<HTMLDivElement | null>(null)
  const [status, setStatus] = useState<ConsoleStatus>("connecting")
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!wrapRef.current) return
    const token = useAuthStore.getState().token
    if (!token) {
      const missingToken = window.setTimeout(() => {
        setError(t("console.error_not_logged_in"))
        setStatus("closed")
      }, 0)
      return () => window.clearTimeout(missingToken)
    }

    const terminal = new Terminal({
      cursorBlink: true,
      fontFamily: '"JetBrains Mono", "Fira Code", Menlo, Consolas, monospace',
      fontSize: 13,
      theme: { background: "#0b111c", foreground: "#e8eef8", cursor: "#69d7ff" },
      convertEol: true,
    })
    const fit = new FitAddon()
    terminal.loadAddon(fit)
    terminal.open(wrapRef.current)
    const safeFit = () => { try { fit.fit() } catch { /* Das Terminal kann während des Schließens bereits getrennt sein. */ } }
    safeFit()
    requestAnimationFrame(safeFit)

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
    const url = `${protocol}//${window.location.host}/api/containers/${containerId}/console?token=${encodeURIComponent(token)}`
    const socket = new WebSocket(url)
    socket.binaryType = "arraybuffer"

    socket.onopen = () => {
      setStatus("connected")
      socket.send(JSON.stringify({ type: "resize", rows: terminal.rows, cols: terminal.cols }))
    }
    socket.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) terminal.write(new Uint8Array(event.data))
      else if (typeof event.data === "string") terminal.write(event.data)
    }
    socket.onerror = () => setError(t("console.error_connection"))
    socket.onclose = (event) => {
      setStatus("closed")
      if (event.code === 4401) setError(t("console.error_unauthorized"))
      else if (event.code === 4404) setError(t("console.error_not_found"))
      else if (event.code === 4409) setError(t("console.error_not_running"))
      else if (event.code === 4500) setError(t("console.error_backend"))
    }

    const onData = terminal.onData((data) => {
      if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: "input", data }))
    })
    const onResize = () => {
      try { fit.fit() } catch { /* Das Terminal kann während des Schließens bereits getrennt sein. */ }
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "resize", rows: terminal.rows, cols: terminal.cols }))
      }
    }
    window.addEventListener("resize", onResize)
    const resizeObserver = new ResizeObserver(onResize)
    resizeObserver.observe(wrapRef.current)
    terminal.focus()

    return () => {
      window.removeEventListener("resize", onResize)
      resizeObserver.disconnect()
      onData.dispose()
      try { socket.close() } catch { /* Die Verbindung kann bereits geschlossen sein. */ }
      terminal.dispose()
    }
  }, [containerId, t])

  return (
    <div className={`flex min-h-0 flex-col bg-[#0b111c] ${className ?? ""}`}>
      {error && <AdminFeedback tone="danger" className="m-2 shrink-0">{error}</AdminFeedback>}
      <div className="min-h-0 flex-1 bg-[#0b111c] p-2" ref={wrapRef} />
      <div className="flex shrink-0 items-center justify-between border-t border-[#2a364b] bg-[#0d1420] px-4 py-2 font-mono text-[11px] text-[#8d9ab0]">
        <span>incus exec — Strg+D zum Beenden</span>
        <AdminStatus tone={STATUS_TONES[status]} dot>{status}</AdminStatus>
      </div>
    </div>
  )
}
