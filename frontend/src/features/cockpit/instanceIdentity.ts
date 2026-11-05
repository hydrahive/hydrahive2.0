export interface InstanceIdentity {
  username: string
  roleLabel: "Nutzer" | "SYSTEM-ADMIN"
  roleBadge: "NUTZER" | "ADMIN"
  host: string
  shortHost: string
  isAdmin: boolean
  buttonLabel: string
  adminWarning: string | null
}

type LocationLike = Pick<Location, "host">

const UNKNOWN_INSTANCE = "unbekannte Instanz"
const ADMIN_WARNING = "System-Admin: Chats und Sitzungen werden getrennt von normalen Benutzerkonten geführt."

/** Liest ausschließlich die Browserinstanz; SSR und Tests erhalten einen sicheren Fallback. */
export function getInstanceHost(location?: LocationLike): string {
  const browserLocation = location ?? (typeof window === "undefined" ? undefined : window.location)
  return browserLocation?.host?.trim() || UNKNOWN_INSTANCE
}

function hostCode(host: string): string {
  let value = 2166136261
  for (const char of host) value = Math.imul(value ^ char.charCodeAt(0), 16777619)
  return (value >>> 0).toString(16).slice(-4).toUpperCase().padStart(4, "0")
}

/** Kurze, aber durch Host-Hash unterscheidbare Kennung für schmale Topbars. */
export function compactInstanceHost(host: string): string {
  if (host.length <= 12) return host
  return `${host.slice(0, 6)}…${hostCode(host)}`
}

/** Formatiert die rein informative Konto- und Instanzanzeige für das Cockpit-Menü. */
export function getInstanceIdentity(username: string | null | undefined, role: string | null | undefined, location?: LocationLike): InstanceIdentity {
  const isAdmin = role === "admin"
  const displayUsername = username || "User"
  const roleLabel = isAdmin ? "SYSTEM-ADMIN" : "Nutzer"
  const roleBadge = isAdmin ? "ADMIN" : "NUTZER"
  const host = getInstanceHost(location)

  return {
    username: displayUsername,
    roleLabel,
    roleBadge,
    host,
    shortHost: compactInstanceHost(host),
    isAdmin,
    buttonLabel: `Benutzermenü: ${displayUsername}, ${roleLabel}, Instanz ${host}`,
    adminWarning: isAdmin ? ADMIN_WARNING : null,
  }
}
