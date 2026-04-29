import { useEffect, useState } from "react"
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

// Modul-Singleton: nur EIN aktives TTS in der ganzen App.
// Mehrere MessageBubbles teilen sich diese Refs — sonst doppelte Stimmen.
let activeAudio: HTMLAudioElement | null = null
let activeAudioUrl: string | null = null
let speakRequestId = 0
const listeners = new Set<(speaking: boolean) => void>()

function setSpeakingGlobal(v: boolean) {
  listeners.forEach((l) => l(v))
}

function stopAll() {
  speakRequestId++ // invalidiert laufende speak()-Promises
  if (activeAudio) {
    activeAudio.onended = null
    activeAudio.onerror = null
    activeAudio.pause()
    activeAudio.src = ""
    activeAudio = null
  }
  if (activeAudioUrl) {
    URL.revokeObjectURL(activeAudioUrl)
    activeAudioUrl = null
  }
  if (typeof window !== "undefined" && window.speechSynthesis) {
    window.speechSynthesis.cancel()
  }
  setSpeakingGlobal(false)
}

async function speakGlobal(text: string, lang = "de-DE") {
  stopAll()
  const myId = ++speakRequestId
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
      if (myId !== speakRequestId) return
      if (!res.ok) throw new Error(`TTS ${res.status}`)
      const blob = await res.blob()
      if (myId !== speakRequestId) return
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audio.onended = () => {
        if (activeAudio === audio) {
          activeAudio = null
          if (activeAudioUrl) { URL.revokeObjectURL(activeAudioUrl); activeAudioUrl = null }
          setSpeakingGlobal(false)
        }
      }
      audio.onerror = () => {
        if (activeAudio === audio) {
          activeAudio = null
          if (activeAudioUrl) { URL.revokeObjectURL(activeAudioUrl); activeAudioUrl = null }
          setSpeakingGlobal(false)
        }
      }
      activeAudio = audio
      activeAudioUrl = url
      setSpeakingGlobal(true)
      await audio.play()
    } catch (e) {
      console.error("MiniMax TTS fehlgeschlagen:", e)
      setSpeakingGlobal(false)
    }
    // KEIN Fallback auf Browser-TTS — entweder/oder, nie beides
    return
  }

  // provider === "browser"
  const utt = new SpeechSynthesisUtterance(text)
  utt.lang = lang
  utt.rate = 1.0
  utt.onstart = () => { if (myId === speakRequestId) setSpeakingGlobal(true) }
  utt.onend = () => { if (myId === speakRequestId) setSpeakingGlobal(false) }
  utt.onerror = () => { if (myId === speakRequestId) setSpeakingGlobal(false) }
  window.speechSynthesis.speak(utt)
}

export function useVoiceOutput() {
  const [speaking, setSpeaking] = useState(false)

  useEffect(() => {
    listeners.add(setSpeaking)
    return () => { listeners.delete(setSpeaking) }
  }, [])

  return {
    speaking,
    speak: (text: string, lang?: string) => speakGlobal(text, lang),
    stop: stopAll,
  }
}
