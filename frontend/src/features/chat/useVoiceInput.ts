import { useRef, useState } from "react"
import { useAuthStore } from "@/features/auth/useAuthStore"

type State = "idle" | "recording" | "transcribing" | "error"

// iOS Safari kann nur audio/mp4. Android Chrome bevorzugt webm.
// Wir wählen den ersten unterstützten MimeType.
const PREFERRED_MIMES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/mp4;codecs=mp4a.40.2",
  "audio/ogg;codecs=opus",
]

function pickMime(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined
  const supported = (MediaRecorder as unknown as { isTypeSupported?: (s: string) => boolean }).isTypeSupported
  if (!supported) return undefined
  for (const m of PREFERRED_MIMES) {
    try { if (supported.call(MediaRecorder, m)) return m } catch { /* */ }
  }
  return undefined
}

export function useVoiceInput(onResult: (text: string) => void) {
  const [state, setState] = useState<State>("idle")
  const stateRef = useRef<State>("idle")
  const mediaRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const mimeRef = useRef<string>("audio/webm")

  function set(s: State) {
    stateRef.current = s
    setState(s)
  }

  function reset(reason: string) {
    console.warn("[voice] reset:", reason)
    try { mediaRef.current?.stream?.getTracks().forEach((t) => t.stop()) } catch { /* */ }
    mediaRef.current = null
    chunksRef.current = []
    set("idle")
  }

  async function toggle() {
    if (stateRef.current === "recording") {
      try {
        try { mediaRef.current?.requestData?.() } catch { /* iOS */ }
        mediaRef.current?.stop()
        set("transcribing")
        // Safety: falls onstop nicht feuert
        setTimeout(() => {
          if (stateRef.current === "transcribing") {
            console.warn("[voice] onstop hat nicht gefeuert — manuell transkribieren")
            void transcribe()
          }
        }, 1500)
      } catch (e) {
        reset(`stop failed: ${e}`)
      }
      return
    }
    if (stateRef.current !== "idle") {
      reset(`unexpected state ${stateRef.current}`)
      return
    }

    if (typeof MediaRecorder === "undefined") {
      console.error("[voice] MediaRecorder nicht unterstützt")
      set("error"); setTimeout(() => set("idle"), 2000); return
    }
    if (typeof window !== "undefined" && !window.isSecureContext) {
      console.error("[voice] kein Secure Context — Mikrofon braucht HTTPS oder localhost")
      set("error"); setTimeout(() => set("idle"), 2000); return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mime = pickMime()
      const recorder = mime
        ? new MediaRecorder(stream, { mimeType: mime })
        : new MediaRecorder(stream)
      mimeRef.current = recorder.mimeType || mime || "audio/webm"
      console.log("[voice] start, mimeType=", mimeRef.current)
      chunksRef.current = []
      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorder.onstop = () => {
        try { stream.getTracks().forEach((t) => t.stop()) } catch { /* */ }
        void transcribe()
      }
      recorder.onerror = (e) => {
        console.error("[voice] recorder error:", e)
        reset("recorder error")
      }
      mediaRef.current = recorder
      // start(250) → ondataavailable alle 250ms — iOS triggert sonst evtl. nie
      recorder.start(250)
      set("recording")
    } catch (e) {
      console.error("[voice] getUserMedia failed:", e)
      set("error"); setTimeout(() => set("idle"), 2000)
    }
  }

  async function transcribe() {
    const mime = mimeRef.current
    const blob = new Blob(chunksRef.current, { type: mime })
    chunksRef.current = []
    console.log("[voice] transcribe blob size=", blob.size, "mime=", mime)
    if (blob.size === 0) { set("idle"); return }
    const form = new FormData()
    const ext = mime.startsWith("audio/mp4") ? "m4a"
              : mime.startsWith("audio/ogg") ? "ogg"
              : "webm"
    form.append("audio", blob, `audio.${ext}`)
    try {
      const token = useAuthStore.getState().token ?? ""
      const res = await fetch("/api/stt", {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: form,
      })
      if (!res.ok) {
        const errText = await res.text().catch(() => "")
        console.error("[voice] STT failed:", res.status, errText)
        throw new Error(`STT ${res.status}`)
      }
      const { text } = await res.json() as { text: string }
      console.log("[voice] STT result:", text)
      if (text) onResult(text)
      set("idle")
    } catch (e) {
      console.error("[voice] transcribe error:", e)
      set("error")
      setTimeout(() => set("idle"), 2000)
    }
  }

  return { state, toggle }
}
