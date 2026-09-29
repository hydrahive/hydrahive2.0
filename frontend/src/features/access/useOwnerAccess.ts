import { useEffect, useState } from "react"
import { api } from "@/shared/api-client"
import type { MyAccess } from "./types"

// Freigaben des Agent-Besitzers laden (für ausgegraute Werkzeuge im Agent-Editor).
// Fehler werden geschluckt: Die Anzeige ist nur ein Hinweis, das Backend sperrt ohnehin.
export function useOwnerAccess(owner: string | null | undefined): MyAccess | null {
  const [access, setAccess] = useState<MyAccess | null>(null)
  useEffect(() => {
    let alive = true
    if (!owner) return
    api.get<MyAccess>(`/access/users/${encodeURIComponent(owner)}`)
      .then((data) => { if (alive) setAccess({ ...data, groups: data.groups ?? [] }) })
      .catch(() => { if (alive) setAccess(null) })
    return () => { alive = false }
  }, [owner])
  return owner ? access : null
}
