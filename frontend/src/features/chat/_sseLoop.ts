/**
 * Gemeinsame SSE-Schleife für die Abos (Session-Live-Sync, Agent-Aktivität).
 *
 * - 401 → onUnauthorized() (Abmelden) und Ende. Früher lief die Schleife mit
 *   ungültigem Token endlos weiter, belegt 27.09.2026: 117× 401 in drei
 *   Minuten (Task a7477846). api-client.ts meldet bei 401 genauso ab.
 * - Andere Fehler oder Verbindungsabriss → neu verbinden mit Backoff
 *   (1,5 s, verdoppelt, höchstens 30 s). Nach einer geglückten Verbindung
 *   startet der Backoff wieder bei 1,5 s.
 * - onFrame bekommt jeden vollständigen Frame (ohne das trennende "\n\n"),
 *   auch wenn er über mehrere Chunks verteilt ankam.
 * fetch und Warten sind injizierbar, damit die Schleife ohne Browser testbar ist.
 */
export const RECONNECT_MIN_MS = 1500
export const RECONNECT_MAX_MS = 30000

export interface SseLoopOptions {
  url: string
  token: () => string | null
  onFrame: (frame: string) => void
  onUnauthorized: () => void
  signal: AbortSignal
  fetchFn?: (url: string, init?: RequestInit) => Promise<Response>
  wait?: (ms: number) => Promise<void>
}

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms))

async function readFrames(res: Response, onFrame: (frame: string) => void): Promise<void> {
  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  while (true) {
    const { done, value } = await reader.read()
    if (done) return
    buffer += decoder.decode(value, { stream: true })
    const frames = buffer.split("\n\n")
    buffer = frames.pop() ?? ""
    for (const frame of frames) onFrame(frame)
  }
}

export async function runSseLoop(opts: SseLoopOptions): Promise<void> {
  const fetchFn = opts.fetchFn ?? ((url, init) => fetch(url, init))
  const wait = opts.wait ?? sleep
  let delay = RECONNECT_MIN_MS
  while (!opts.signal.aborted) {
    try {
      const token = opts.token()
      const res = await fetchFn(opts.url, {
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        signal: opts.signal,
      })
      if (res.status === 401) {
        opts.onUnauthorized()
        return
      }
      if (res.ok && res.body) {
        delay = RECONNECT_MIN_MS
        await readFrames(res, opts.onFrame)
      }
    } catch {
      if (opts.signal.aborted) return
    }
    if (opts.signal.aborted) return
    await wait(delay)
    delay = Math.min(delay * 2, RECONNECT_MAX_MS)
  }
}
