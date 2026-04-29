import { useRef, useState } from "react"

type State = "idle" | "recording" | "transcribing" | "error"

export function useVoiceInput(onResult: (text: string) => void) {
  const [state, setState] = useState<State>("idle")
  const mediaRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  async function start() {
    if (state !== "idle") return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop())
        void transcribe()
      }
      mediaRef.current = recorder
      recorder.start()
      setState("recording")
    } catch {
      setState("error")
      setTimeout(() => setState("idle"), 2000)
    }
  }

  function stop() {
    if (state !== "recording") return
    mediaRef.current?.stop()
    setState("transcribing")
  }

  async function transcribe() {
    const blob = new Blob(chunksRef.current, { type: "audio/webm" })
    const form = new FormData()
    form.append("audio", blob, "audio.webm")
    try {
      const token = localStorage.getItem("hh_token") ?? ""
      const res = await fetch("/api/stt", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      })
      if (!res.ok) throw new Error(`${res.status}`)
      const { text } = await res.json() as { text: string }
      if (text) onResult(text)
      setState("idle")
    } catch {
      setState("error")
      setTimeout(() => setState("idle"), 2000)
    }
  }

  return { state, start, stop }
}
