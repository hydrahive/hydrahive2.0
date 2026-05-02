import { useEffect, useState } from "react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import type { WhatsAppConfig } from "./api"

interface MmxVoice { voice_id: string; voice_name: string }

interface Props {
  cfg: WhatsAppConfig
  onChange: (cfg: WhatsAppConfig) => void
}

export function WhatsAppVoiceSection({ cfg, onChange }: Props) {
  const [voices, setVoices] = useState<MmxVoice[]>([])
  const [voicesErr, setVoicesErr] = useState<string | null>(null)

  useEffect(() => {
    if (!cfg.respond_as_voice) return
    if (voices.length > 0) return
    const token = useAuthStore.getState().token ?? ""
    const headers = token ? { Authorization: `Bearer ${token}` } : undefined
    const langs = ["german", "english", "french", "spanish", "italian",
                   "chinese", "japanese", "russian", "portuguese", "arabic"]
    Promise.all(langs.map((lang) =>
      fetch(`/api/tts/voices?language=${lang}`, { headers })
        .then((r) => r.ok ? r.json() : { voices: [] })
        .then((d: { voices: MmxVoice[] }) => (d.voices ?? []).map((v) => ({ ...v, lang })))
        .catch(() => [])
    )).then((results) => {
      const all: (MmxVoice & { lang: string })[] = results.flat()
      const seen = new Set<string>()
      const unique = all.filter((v) => { if (seen.has(v.voice_id)) return false; seen.add(v.voice_id); return true })
      setVoices(unique)
      if (unique.length === 0) setVoicesErr("Keine Voices vom mmx-CLI geladen")
    })
  }, [cfg.respond_as_voice, voices.length])

  return (
    <div className="space-y-2">
      <div>
        <label className="text-[11px] text-zinc-500">Sprache der eingehenden Sprachnachrichten</label>
        <select value={cfg.stt_language || ""}
          onChange={(e) => onChange({ ...cfg, stt_language: e.target.value })}
          className="mt-1 w-full rounded-lg bg-zinc-900 border border-white/[8%] px-2.5 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-violet-500/50 [&>option]:bg-zinc-900 [&>option]:text-zinc-100">
          <option value="">Auto-Erkennung</option>
          <option value="de">Deutsch</option>
          <option value="en">English</option>
          <option value="fr">Français</option>
          <option value="es">Español</option>
          <option value="it">Italiano</option>
        </select>
        <p className="text-[10px] text-zinc-600 mt-1">
          Auto-Erkennung ist robust ab ~3s Audio. Bei sehr kurzen Voices lieber explizit setzen.
        </p>
      </div>

      <label className="flex items-center gap-1.5 text-xs cursor-pointer text-zinc-300">
        <input type="checkbox" checked={cfg.respond_as_voice}
          onChange={(e) => onChange({ ...cfg, respond_as_voice: e.target.checked })}
          className="h-3 w-3 rounded" />
        Antworten als Sprachnachricht senden
      </label>

      {cfg.respond_as_voice && (
        <div>
          <label className="text-[11px] text-zinc-500">Stimme (MiniMax)</label>
          <select value={cfg.voice_name}
            onChange={(e) => onChange({ ...cfg, voice_name: e.target.value })}
            className="mt-1 w-full rounded-lg bg-zinc-900 border border-white/[8%] px-2.5 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-violet-500/50 [&>option]:bg-zinc-900 [&>option]:text-zinc-100">
            {!voices.find((v) => v.voice_id === cfg.voice_name) && (
              <option value={cfg.voice_name}>{cfg.voice_name}</option>
            )}
            {[...voices].sort((a, b) => a.voice_id.localeCompare(b.voice_id)).map((v) => (
              <option key={v.voice_id} value={v.voice_id}>
                {v.voice_id}{v.voice_name && v.voice_name !== v.voice_id ? ` — ${v.voice_name}` : ""}
              </option>
            ))}
          </select>
          {voicesErr && <p className="text-[10px] text-rose-400 mt-1">Voices-Liste nicht ladbar: {voicesErr}</p>}
          {!voicesErr && voices.length === 0 && <p className="text-[10px] text-zinc-600 mt-1">Lade Stimmen…</p>}
        </div>
      )}
    </div>
  )
}
