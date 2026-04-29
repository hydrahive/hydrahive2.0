import { useEffect, useState } from "react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import {
  DEFAULT_VOICE,
  TTS_PROVIDER_KEY,
  TTS_VOICE_KEY,
  type TTSProvider,
} from "@/features/chat/useVoiceOutput"

interface MmxVoice {
  voice_id: string
  voice_name: string
  description?: string[]
}

export function TTSSettings() {
  const [provider, setProvider] = useState<TTSProvider>(
    (localStorage.getItem(TTS_PROVIDER_KEY) as TTSProvider | null) ?? "browser"
  )
  const [voice, setVoice] = useState<string>(
    localStorage.getItem(TTS_VOICE_KEY) ?? DEFAULT_VOICE
  )
  const [voices, setVoices] = useState<MmxVoice[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (provider !== "minimax") return
    setLoading(true)
    setError(null)
    const token = useAuthStore.getState().token ?? ""
    fetch("/api/tts/voices?language=german", {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.ok ? r.json() : Promise.reject(new Error(`${r.status}`)))
      .then((d: { voices: MmxVoice[] }) => setVoices(d.voices ?? []))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false))
  }, [provider])

  function changeProvider(p: TTSProvider) {
    setProvider(p)
    localStorage.setItem(TTS_PROVIDER_KEY, p)
  }

  function changeVoice(v: string) {
    setVoice(v)
    localStorage.setItem(TTS_VOICE_KEY, v)
  }

  return (
    <div className="rounded-xl border border-white/[8%] bg-white/[2%] p-5 space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-zinc-200">Sprachausgabe</h2>
        <p className="text-xs text-zinc-500 mt-0.5">Wähle die Stimme für vorgelesene Antworten.</p>
      </div>
      <div className="space-y-2">
        <label className="block text-xs text-zinc-400">Anbieter</label>
        <div className="flex gap-2">
          <button
            onClick={() => changeProvider("browser")}
            className={`px-3 py-1.5 rounded-lg text-xs border transition-colors ${
              provider === "browser"
                ? "bg-violet-500/20 border-violet-500/40 text-violet-200"
                : "bg-white/[3%] border-white/[8%] text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Browser (Standard)
          </button>
          <button
            onClick={() => changeProvider("minimax")}
            className={`px-3 py-1.5 rounded-lg text-xs border transition-colors ${
              provider === "minimax"
                ? "bg-violet-500/20 border-violet-500/40 text-violet-200"
                : "bg-white/[3%] border-white/[8%] text-zinc-400 hover:text-zinc-200"
            }`}
          >
            MiniMax (Cloud, hochwertig)
          </button>
        </div>
      </div>

      {provider === "minimax" && (
        <div className="space-y-2">
          <label className="block text-xs text-zinc-400">Stimme</label>
          {loading && <p className="text-xs text-zinc-500">Lade Stimmen…</p>}
          {error && <p className="text-xs text-rose-400">Fehler: {error}</p>}
          {!loading && !error && voices.length > 0 && (
            <select
              value={voice}
              onChange={(e) => changeVoice(e.target.value)}
              className="w-full max-w-md bg-zinc-900 border border-white/[10%] rounded-lg px-3 py-1.5 text-sm text-zinc-200"
            >
              {voices.map((v) => (
                <option key={v.voice_id} value={v.voice_id}>
                  {v.voice_name} — {v.description?.[0] ?? v.voice_id}
                </option>
              ))}
            </select>
          )}
          {!loading && !error && voices.length === 0 && (
            <p className="text-xs text-zinc-500">Keine Stimmen gefunden — mmx CLI installiert &amp; eingeloggt?</p>
          )}
        </div>
      )}
    </div>
  )
}
