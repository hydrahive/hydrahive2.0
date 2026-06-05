import { useAuthStore } from "@/features/auth/useAuthStore"
import { api } from "@/shared/api-client"
import type { ModulesIndex } from "./types"

const BASE = "/admin/modules"

function authHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function listModules(): Promise<ModulesIndex> {
  return api.get<ModulesIndex>(BASE)
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
    if (!r.ok || !r.body) { onError(`HTTP ${r.status}`); return }
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

export function updateModule(
  id: string,
  onLine: (line: string) => void,
  onDone: () => void,
  onError: (msg: string) => void,
): () => void {
  return stream(`/${id}/update`, "POST", onLine, onDone, onError)
}
