/** Nur Tailscale-Adressen erreichen /api/peering/ (nginx: 100.64.0.0/10, fd7a:115c:a1e0::/48). */
export function isTailnetUrl(raw: string): boolean {
  let host: string
  try {
    host = new URL(raw).hostname.toLowerCase()
  } catch {
    return false
  }
  if (host.endsWith(".ts.net")) return true
  if (host.startsWith("[")) return /^\[fd7a:115c:a1e0:/.test(host)
  const m = host.match(/^(\d{1,3})\.(\d{1,3})\.\d{1,3}\.\d{1,3}$/)
  if (!m) return false
  const [a, b] = [Number(m[1]), Number(m[2])]
  return a === 100 && b >= 64 && b <= 127
}
