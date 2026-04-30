import { useEffect, useRef, useState } from "react"
import RFB from "@novnc/novnc"
import { Maximize2, X } from "lucide-react"
import { vmsApi } from "./api"
import type { VM } from "./types"

interface Props {
  vm: VM
  onClose: () => void
}

export function VMConsoleModal({ vm, onClose }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const rfbRef = useRef<RFB | null>(null)
  const [status, setStatus] = useState<"connecting" | "connected" | "disconnected" | "error">("connecting")
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    async function connect() {
      if (!containerRef.current) return
      try {
        const info = await vmsApi.vncInfo(vm.vm_id)
        if (!alive) return
        const proto = window.location.protocol === "https:" ? "wss:" : "ws:"
        const url = `${proto}//${window.location.host}${info.ws_path}?token=${encodeURIComponent(info.token)}`
        const rfb = new RFB(containerRef.current, url, {
          credentials: { password: "" },
        })
        rfb.scaleViewport = true
        rfb.resizeSession = false
        rfb.background = "#000"
        rfb.addEventListener("connect", () => alive && setStatus("connected"))
        rfb.addEventListener("disconnect", (e: any) => {
          if (!alive) return
          setStatus("disconnected")
          if (e?.detail?.clean === false) {
            setError(e.detail.reason || "Verbindung getrennt")
          }
        })
        rfb.addEventListener("securityfailure", (e: any) => {
          if (!alive) return
          setStatus("error")
          setError(e?.detail?.reason || "Authentifizierung fehlgeschlagen")
        })
        rfbRef.current = rfb
      } catch (e) {
        if (!alive) return
        setStatus("error")
        setError(e instanceof Error ? e.message : String(e))
      }
    }
    void connect()
    return () => {
      alive = false
      if (rfbRef.current) {
        try { rfbRef.current.disconnect() } catch { /* */ }
        rfbRef.current = null
      }
    }
  }, [vm.vm_id])

  function sendCtrlAltDel() {
    rfbRef.current?.sendCtrlAltDel()
  }
  function fullscreen() {
    containerRef.current?.requestFullscreen?.()
  }

  return (
    <div className="fixed inset-0 z-40 bg-black/80 backdrop-blur-sm flex items-center justify-center" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="w-full max-w-5xl h-[80vh] mx-4 rounded-2xl border border-white/[8%] bg-zinc-900 shadow-2xl flex flex-col">
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/[6%]">
          <div className="flex items-center gap-3">
            <h2 className="text-base font-bold text-white">{vm.name}</h2>
            <StatusPill status={status} />
          </div>
          <div className="flex items-center gap-2">
            <button onClick={sendCtrlAltDel}
              className="px-2 py-1 rounded-md bg-white/[5%] hover:bg-white/[10%] text-xs text-zinc-300"
              title="Strg+Alt+Entf an die VM senden">
              Ctrl+Alt+Del
            </button>
            <button onClick={fullscreen} className="p-1.5 rounded text-zinc-400 hover:text-zinc-200 hover:bg-white/5">
              <Maximize2 size={14} />
            </button>
            <button onClick={onClose} className="p-1.5 rounded text-zinc-400 hover:text-zinc-200 hover:bg-white/5">
              <X size={16} />
            </button>
          </div>
        </div>
        <div ref={containerRef} className="flex-1 bg-black overflow-hidden" />
        {error && (
          <div className="px-5 py-2 border-t border-white/[6%] text-xs text-rose-300 bg-rose-500/10">
            {error}
          </div>
        )}
        <div className="px-5 py-2 border-t border-white/[6%] text-[11px] text-zinc-500">
          Tipp: Browser-Tastenkombinationen (Strg+W, Strg+T) gehen an den Browser, nicht an die VM. Vollbild-Modus umgeht das.
        </div>
      </div>
    </div>
  )
}

function StatusPill({ status }: { status: "connecting" | "connected" | "disconnected" | "error" }) {
  const map = {
    connecting:   { text: "Verbinde…", cls: "bg-amber-500/15 text-amber-300 ring-amber-500/30" },
    connected:    { text: "Verbunden", cls: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30" },
    disconnected: { text: "Getrennt",  cls: "bg-zinc-500/15 text-zinc-300 ring-zinc-500/30" },
    error:        { text: "Fehler",    cls: "bg-rose-500/15 text-rose-300 ring-rose-500/30" },
  }
  const s = map[status]
  return (
    <span className={`px-2 py-0.5 rounded-full text-[11px] ring-1 ${s.cls}`}>{s.text}</span>
  )
}
