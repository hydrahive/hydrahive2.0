/** Spiegelt has_concrete_host() aus credentials/models.py: Schema + Host ohne "*",
 *  oder "*." + Domain mit Punkt. Nur dann setzt fetch_url den Zugang ein. */
export function hasConcreteHost(pattern: string): boolean {
  const p = pattern.trim()
  const i = p.indexOf("://")
  if (i < 0) return false
  let authority = p.slice(i + 3).split(/[/?#]/, 1)[0]
  authority = authority.slice(authority.lastIndexOf("@") + 1)
  let host = authority.startsWith("[")
    ? authority.slice(1, authority.indexOf("]") > 0 ? authority.indexOf("]") : undefined)
    : authority.replace(/:(\d+|\*)$/, "")
  if (host.startsWith("*.")) {
    host = host.slice(2)
    if (!host.includes(".")) return false
  }
  return !host.includes("*") && /[A-Za-z0-9]/.test(host)
}
