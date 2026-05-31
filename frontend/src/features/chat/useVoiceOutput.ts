import { useEffect, useState } from "react"
import { useAuthStore } from "@/features/auth/useAuthStore"

export type TTSProvider = "browser" | "local" | "minimax" | "openrouter"

export const TTS_PROVIDER_KEY = "hh_tts_provider"
export const TTS_VOICE_KEY = "hh_tts_voice"
export const DEFAULT_VOICE = "German_FriendlyMan"

export function getTTSProvider(): TTSProvider {
  const v = localStorage.getItem(TTS_PROVIDER_KEY)
  return v === "local" || v === "minimax" || v === "openrouter" ? v : "browser"
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
const errorListeners = new Set<(error: string | null) => void>()
let errorTimer: ReturnType<typeof setTimeout> | null = null

function setSpeakingGlobal(v: boolean) {
  listeners.forEach((l) => l(v))
}

function setErrorGlobal(msg: string | null) {
  errorListeners.forEach((l) => l(msg))
  if (errorTimer) { clearTimeout(errorTimer); errorTimer = null }
  // Fehlermeldung nach 6s automatisch wieder ausblenden.
  if (msg) errorTimer = setTimeout(() => errorListeners.forEach((l) => l(null)), 6000)
}

async function ttsErrorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json()
    const detail = body?.detail?.params?.message ?? body?.detail?.message ?? body?.detail
    if (typeof detail === "string" && detail) return `Vorlesen fehlgeschlagen (${res.status}): ${detail}`
  } catch { /* kein JSON-Body */ }
  return `Vorlesen fehlgeschlagen (${res.status})`
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
  setErrorGlobal(null)
  const myId = ++speakRequestId
  const provider = getTTSProvider()

  if (provider === "local" || provider === "minimax" || provider === "openrouter") {
    try {
      const token = useAuthStore.getState().token ?? ""
      // local (Piper) nutzt die Container-Stimme — keine Voice mitschicken.
      const voice = provider === "local" ? "" : getTTSVoice()
      const res = await fetch("/api/tts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ text, voice, provider }),
      })
      if (myId !== speakRequestId) return
      if (!res.ok) throw new Error(await ttsErrorMessage(res))
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
      try {
        await audio.play()
      } catch (playErr) {
        // play() wird abgebrochen wenn die Quelle während des Starts entfernt
        // wird (erneuter Klick / stop / Unmount) — kein echter Fehler.
        if (playErr instanceof DOMException && playErr.name === "AbortError") return
        throw playErr
      }
    } catch (e) {
      console.error(`TTS (${provider}) fehlgeschlagen:`, e)
      setErrorGlobal(e instanceof Error ? e.message : `Vorlesen (${provider}) fehlgeschlagen`)
      setSpeakingGlobal(false)
    }
    // KEIN Fallback auf Browser-TTS — entweder/oder, nie beides
    return
  }

  // provider === "browser"
  // Voices-Loading-Race: nach Page-Reload sind Voices oft noch nicht da.
  // getVoices() returnt leeres Array und speak() failed silent. Einmal auf
  // voiceschanged warten falls leer.
  if (typeof window !== "undefined" && window.speechSynthesis) {
    const sx = window.speechSynthesis
    if (sx.getVoices().length === 0) {
      await new Promise<void>((resolve) => {
        const onChange = () => {
          sx.removeEventListener("voiceschanged", onChange)
          resolve()
        }
        sx.addEventListener("voiceschanged", onChange)
        // Fallback-Timeout damit wir nicht ewig hängen wenn der Browser
        // voiceschanged nicht feuert.
        setTimeout(() => { sx.removeEventListener("voiceschanged", onChange); resolve() }, 500)
      })
      if (myId !== speakRequestId) return
    }
  }
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
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listeners.add(setSpeaking)
    errorListeners.add(setError)
    return () => { listeners.delete(setSpeaking); errorListeners.delete(setError) }
  }, [])

  return {
    speaking,
    error,
    speak: (text: string, lang?: string) => speakGlobal(text, lang),
    stop: stopAll,
  }
}
