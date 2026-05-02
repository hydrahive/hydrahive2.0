import { useState } from "react"
import { systemApi } from "./api"
import type { VoiceInstallState } from "./VoiceInstallModal"

export function useVoiceInstall() {
  const [state, setState] = useState<"idle" | VoiceInstallState>("idle")
  const [error, setError] = useState<string | null>(null)

  function begin() { setState("confirm"); setError(null) }
  function close() { setState("idle") }

  async function confirm() {
    setState("starting")
    setError(null)
    try {
      await systemApi.installVoice()
      setState("running")
      const startedAt = Date.now()
      while (Date.now() - startedAt < 300_000) {
        await new Promise((r) => setTimeout(r, 3000))
        try {
          const log = await systemApi.voiceLog(50)
          if (log.lines.join("").includes("Voice Interface bereit")) {
            setState("done")
            return
          }
        } catch { /* ignore */ }
      }
      setState("done")
    } catch (e) {
      setState("failed")
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  return { state, error, begin, close, confirm }
}
