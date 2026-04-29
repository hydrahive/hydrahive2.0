import { useRef, useState } from "react"

type State = "idle" | "recording" | "transcribing" | "error"

export function useVoiceInput(onResult: (text: string) => void) {
  const [state, setState] = useState<State>("idle")
  const stateRef = useRef<State>("idle")
  const mediaRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const stopRequestedRef = useRef(false)

  function set(s: State) {
    stateRef.current = s
    setState(s)
  }

  async function start() {
    if (stateRef.current !== "idle") return
    stopRequestedRef.current = false
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      // stop() might have been called while getUserMedia was waiting (quick tap)
      if (stopRequestedRef.current) {
        stream.getTracks().forEach((t) => t.stop())
        return
      }
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      recorder.onstop = () => { stream.getTracks().forEach((t) => t.stop()); void transcribe() }
      mediaRef.current = recorder
      recorder.start()
      set("recording")
      // stop() might have been called between recorder.start() and set("recording")
      if (stopRequestedRef.current) {
        recorder.stop()
        set("transcribing")
      }
    } catch {
      set("error")
      setTimeout(() => set("idle"), 2000)
    }
  }

  function stop() {
    if (stateRef.current === "recording") {
      mediaRef.current?.stop()
      set("transcribing")
    } else {
      // start() still in flight (getUserMedia not resolved yet)
      stopRequestedRef.current = true
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

  return { state, start, stop }
}
