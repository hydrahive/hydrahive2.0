import { useAuthStore } from "@/features/auth/useAuthStore"
import { api } from "@/shared/api-client"
import type { ThemesIndex } from "./types"

const BASE = "/admin/themes"

function authHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function listThemes(): Promise<ThemesIndex> {
  return api.get<ThemesIndex>(BASE)
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

export function installTheme(
  id: string,
  onLine: (line: string) => void,
  onDone: () => void,
  onError: (msg: string) => void,
): () => void {
  return stream(`/${id}/install`, "POST", onLine, onDone, onError)
}

export function uninstallTheme(
  id: string,
  onLine: (line: string) => void,
  onDone: () => void,
  onError: (msg: string) => void,
): () => void {
  return stream(`/${id}`, "DELETE", onLine, onDone, onError)
}

export function updateTheme(
  id: string,
  onLine: (line: string) => void,
  onDone: () => void,
  onError: (msg: string) => void,
): () => void {
  return stream(`/${id}/update`, "POST", onLine, onDone, onError)
}

// --- Editor-API (Etappe 2/3): Templates lesen/schreiben, forken, publishen ---

export interface TemplateList {
  theme_id: string
  routes: string[]
  protected: boolean
}
export interface TemplateContent {
  theme_id: string
  route: string
  html: string
}

export function listTemplates(themeId: string): Promise<TemplateList> {
  return api.get<TemplateList>(`${BASE}/${themeId}/templates`)
}

export function getTemplate(themeId: string, route: string): Promise<TemplateContent> {
  return api.get<TemplateContent>(`${BASE}/${themeId}/templates/${route}`)
}

export function saveTemplate(themeId: string, route: string, html: string): Promise<unknown> {
  return api.put(`${BASE}/${themeId}/templates/${route}`, { html })
}

export function forkTheme(
  sourceId: string,
  newId: string,
  newName: string,
): Promise<{ id: string; name: string; source: string }> {
  return api.post(`${BASE}/${sourceId}/fork`, { new_id: newId, new_name: newName })
}

export function publishTheme(
  id: string,
  onLine: (line: string) => void,
  onDone: () => void,
  onError: (msg: string) => void,
): () => void {
  return stream(`/${id}/publish`, "POST", onLine, onDone, onError)
}
