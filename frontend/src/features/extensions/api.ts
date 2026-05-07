import type { Extension } from "./types"

const BASE = "/api/admin/extensions"

export async function fetchExtensions(): Promise<Extension[]> {
  const r = await fetch(BASE, { credentials: "include" })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

export function streamAction(
  id: string,
  action: "install" | "uninstall",
  params: Record<string, string>,
  onLine: (line: string) => void,
  onDone: () => void,
  onError: (msg: string) => void,
): () => void {
  let closed = false
  const ctrl = new AbortController()

  fetch(`${BASE}/${id}/${action}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ params }),
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
