import { useAuthStore } from "@/features/auth/useAuthStore"
import { api } from "@/shared/api-client"
import type { Extension } from "./types"

const BASE = "/admin/extensions"

export async function fetchExtensions(): Promise<Extension[]> {
  return api.get<Extension[]>(BASE)
}

export function authHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function streamAction(
  id: string,
  action: "install" | "uninstall",
  params: Record<string, string>,
  onLine: (line: string) => void,
  onDone: () => void,
  onError: (msg: string) => void,
  mode: "native" | "docker" = "native",
): () => void {
  let closed = false
  const ctrl = new AbortController()

  fetch(`/api${BASE}/${id}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ params, mode }),
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
        } catch {}
      }
    }
  }).catch((e) => {
    if (!closed) onError(String(e))
  })

  return () => { closed = true; ctrl.abort() }
}
