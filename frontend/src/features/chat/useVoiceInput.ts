import { useRef, useState } from "react"

type State = "idle" | "recording" | "transcribing" | "error"

export function useVoiceInput(onResult: (text: string) => void) {
  const [state, setState] = useState<State>("idle")
  const stateRef = useRef<State>("idle")
  const mediaRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  function set(s: State) {
    stateRef.current = s
    setState(s)
  }

  async function toggle() {
    if (stateRef.current === "recording") {
      mediaRef.current?.stop()
      set("transcribing")
      return
    }
    if (stateRef.current !== "idle") return

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      recorder.onstop = () => { stream.getTracks().forEach((t) => t.stop()); void transcribe() }
      mediaRef.current = recorder
      recorder.start()
      set("recording")
    } catch {
      set("error")
      setTimeout(() => set("idle"), 2000)
    }
  }

  async function transcribe() {
    const blob = new Blob(chunksRef.current, { type: "audio/webm" })
    if (blob.size === 0) { set("idle"); return }
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
      set("idle")
    } catch {
      set("error")
      setTimeout(() => set("idle"), 2000)
    }
  }

  return { state, toggle }
}
