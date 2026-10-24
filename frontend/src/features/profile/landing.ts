// Startseite nach dem Anmelden (docs/specs/startdesktop.md, Punkt 4). Gespeichert am Server (preferences.landing).
export const LANDINGS = ["start", "buddy", "dashboard"] as const
export type Landing = (typeof LANDINGS)[number]

/** Alte, nur im Browser gespeicherte Wahl (vor dem Startdesktop). */
export const LEGACY_KEY = "hh_landing"

const PATHS: Record<Landing, string> = { start: "/start", buddy: "/buddy", dashboard: "/dashboard" }
const isLanding = (v: unknown): v is Landing => typeof v === "string" && (LANDINGS as readonly string[]).includes(v)

export function landingPath(landing: Landing): string {
  return PATHS[landing]
}

/**
 * Welche Startseite gilt. Der Server gewinnt; steht dort nur der Standard „start“ und im Browser noch eine
 * alte Wahl (buddy/dashboard), wird diese übernommen und soll an den Server geschrieben werden (migrate).
 */
export function resolveLanding(server: Landing, legacy: string | null): { landing: Landing; migrate: boolean } {
  const s = isLanding(server) ? server : "start"
  if (s !== "start") return { landing: s, migrate: false }
  if (isLanding(legacy) && legacy !== "start") return { landing: legacy, migrate: true }
  return { landing: "start", migrate: false }
}
