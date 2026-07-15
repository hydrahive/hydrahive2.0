import { useState } from "react"
import { useTranslation } from "react-i18next"
import { authHeaders } from "@/features/extensions/api"

/** Docker-Installation als SSE-Stream (aus ExtensionsPage ausgelagert, damit das
 *  Overlay schlank unter ~200 Zeilen bleibt). onDone wird bei Abschluss gerufen. */
export function useDockerInstall(onDone: () => void) {
  const { t } = useTranslation("extensions")
  const [log, setLog] = useState<string[] | null>(null)
  const [installing, setInstalling] = useState(false)

  async function install() {
    setInstalling(true)
    setLog([t("docker.log_starting")])
    try {
      const res = await fetch("/api/admin/extensions/install-docker", { method: "POST", headers: authHeaders() })
      if (!res.ok || !res.body) {
        setLog((l) => [...(l ?? []), `[FEHLER] HTTP ${res.status}`])
        setInstalling(false)
        return
      }
      const reader = res.body.getReader()
      const dec = new TextDecoder()
      let buf = ""
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += dec.decode(value, { stream: true })
        const parts = buf.split("\n\n")
        buf = parts.pop() ?? ""
        for (const part of parts) {
          const dataLine = part.split("\n").find((l) => l.startsWith("data:"))
          if (!dataLine) continue
          try {
            const obj = JSON.parse(dataLine.slice(5).trim())
            if (obj.line !== undefined) setLog((l) => [...(l ?? []), obj.line])
            if (obj.done) { onDone(); break }
          } catch { /* unvollständige SSE-Zeile überspringen */ }
        }
      }
    } catch (e) {
      setLog((l) => [...(l ?? []), `[FEHLER] ${String(e)}`])
    }
    setInstalling(false)
  }

  return { log, installing, install }
}
