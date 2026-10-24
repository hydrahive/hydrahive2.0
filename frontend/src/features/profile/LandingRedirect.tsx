// „/“ → gewählte Startseite (docs/specs/startdesktop.md, Punkt 4). Wahl am Server; alte Browser-Wahl wird
// einmal übernommen. Während des Ladens nichts zeigen (kurz), bei Fehler → Startseite.
import { useEffect, useState } from "react"
import { Navigate } from "react-router-dom"
import { preferencesApi } from "@/features/preferences/api"
import { LEGACY_KEY, landingPath, resolveLanding, type Landing } from "./landing"

function readLegacy(): string | null {
  try { return localStorage.getItem(LEGACY_KEY) } catch { return null }
}

export function LandingRedirect() {
  const [target, setTarget] = useState<string | null>(null)
  useEffect(() => {
    let alive = true
    preferencesApi.get()
      .then((p) => {
        const { landing, migrate } = resolveLanding(p.landing as Landing, readLegacy())
        if (migrate) preferencesApi.patch({ landing }).then(() => { try { localStorage.removeItem(LEGACY_KEY) } catch { /* egal */ } }).catch(() => {})
        if (alive) setTarget(landingPath(landing))
      })
      .catch(() => { if (alive) setTarget("/start") })
    return () => { alive = false }
  }, [])
  return target ? <Navigate to={target} replace /> : null
}
