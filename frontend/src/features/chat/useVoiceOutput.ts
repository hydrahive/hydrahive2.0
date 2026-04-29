import { useRef, useState } from "react"
import { useAuthStore } from "@/features/auth/useAuthStore"

export type TTSProvider = "browser" | "minimax"

export const TTS_PROVIDER_KEY = "hh_tts_provider"
export const TTS_VOICE_KEY = "hh_tts_voice"
export const DEFAULT_VOICE = "German_FriendlyMan"

export function getTTSProvider(): TTSProvider {
  const v = localStorage.getItem(TTS_PROVIDER_KEY)
  return v === "minimax" ? "minimax" : "browser"
}

export function getTTSVoice(): string {
  return localStorage.getItem(TTS_VOICE_KEY) ?? DEFAULT_VOICE
}

export function useVoiceOutput() {
  const [speaking, setSpeaking] = useState(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const uttRef = useRef<SpeechSynthesisUtterance | null>(null)

  function stop() {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.src = ""
      audioRef.current = null
    }
    window.speechSynthesis.cancel()
    setSpeaking(false)
  }

  async function speak(text: string, lang = "de-DE") {
    stop()
    const provider = getTTSProvider()
    if (provider === "minimax") {
      try {
        const token = useAuthStore.getState().token ?? ""
        const res = await fetch("/api/tts", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ text, voice: getTTSVoice() }),
        })
        if (!res.ok) throw new Error(`TTS ${res.status}`)
        const blob = await res.blob()
        const url = URL.createObjectURL(blob)
        const audio = new Audio(url)
        audio.onended = () => { setSpeaking(false); URL.revokeObjectURL(url) }
        audio.onerror = () => { setSpeaking(false); URL.revokeObjectURL(url) }
        audioRef.current = audio
        setSpeaking(true)
        await audio.play()
        return
      } catch (e) {
        console.error("MiniMax TTS fehlgeschlagen, Fallback Browser:", e)
        // fall through to browser
      }
    }
    const utt = new SpeechSynthesisUtterance(text)
    utt.lang = lang
    utt.rate = 1.0
    utt.onstart = () => setSpeaking(true)
    utt.onend = () => setSpeaking(false)
    utt.onerror = () => setSpeaking(false)
    uttRef.current = utt
    window.speechSynthesis.speak(utt)
  }

  return { speaking, speak, stop }
}
