import { useAuthStore } from "@/features/auth/useAuthStore"
import { api, buildErrorMessage } from "@/shared/api-client"
import type { ModulesIndex } from "./types"

const BASE = "/admin/modules"

function authHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function listModules(): Promise<ModulesIndex> {
  return api.get<ModulesIndex>(BASE)
}

/** Anzahl installierter Module mit verfügbarem Update (billig, für den Footer). */
export function getModuleUpdateCount(): Promise<{ count: number }> {
  return api.get<{ count: number }>(`${BASE}/update-count`)
}

function stream(
  path: string,
  method: "POST" | "DELETE",
  onLine: (line: string) => void,
  onDone: () => void,
  onError: (msg: string) => void,
): () => void {
  let closed = false
  const ctrl = new AbortController()

  fetch(`/api${BASE}${path}`, {
    method,
    headers: authHeaders(),
    signal: ctrl.signal,
  }).then(async (r) => {
    if (!r.ok || !r.body) {
      // Fehler mit Code (z. B. 409 „läuft schon“) übersetzt anzeigen, sonst wie bisher „HTTP …“
      const body = await r.json().catch(() => null) as { detail?: unknown } | null
      onError(body ? buildErrorMessage(body, r.status) : `HTTP ${r.status}`)
      return
    }
    const reader = r.body.getReader()
    const dec = new TextDecoder()
    let buf = ""
    while (true) {
      const { done, value } = await reader.read()
      if (done || closed) break
      buf += dec.decode(value, { stream: true })
      const parts = buf.split("\n\n")
      buf = parts.pop() ?? ""
      for (const part of parts) {
        const dataLine = part.split("\n").find((l) => l.startsWith("data:"))
        if (!dataLine) continue
        try {
          const obj = JSON.parse(dataLine.slice(5).trim())
          if (obj.done) { onDone(); return }
          if (obj.error) { onError(String(obj.error)); return }
          if (obj.line !== undefined) onLine(obj.line)
        } catch { /* keepalive */ }
      }
    }
  }).catch((e) => {
    if (!closed) onError(String(e))
  })

  return () => { closed = true; ctrl.abort() }
}

export function installModule(
  id: string,
  onLine: (line: string) => void,
  onDone: () => void,
  onError: (msg: string) => void,
): () => void {
  return stream(`/${id}/install`, "POST", onLine, onDone, onError)
}

export function uninstallModule(
  id: string,
  onLine: (line: string) => void,
  onDone: () => void,
  onError: (msg: string) => void,
): () => void {
  return stream(`/${id}`, "DELETE", onLine, onDone, onError)
}

/** Alle Module mit verfügbarem Update in EINEM Ablauf (einmal bauen, einmal Neustart) – docs/specs/modul-update-alle.md. */
export function updateAllModules(
  onLine: (line: string) => void,
  onDone: () => void,
  onError: (msg: string) => void,
): () => void {
  return stream("/update-all", "POST", onLine, onDone, onError)
}

export function updateModule(
  id: string,
  onLine: (line: string) => void,
  onDone: () => void,
  onError: (msg: string) => void,
): () => void {
  return stream(`/${id}/update`, "POST", onLine, onDone, onError)
}
