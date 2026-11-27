import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { api } from "@/shared/api-client"

export interface AreaInfo {
  id: string
  group: string
  name: string
  sentence: string
  marks: string[]
  tools: string[]
}
export interface AreaGroup { id: string; name: string }
export interface AreaCatalog { groups: AreaGroup[]; areas: AreaInfo[]; unassigned: string[]; never: Set<string>; neverAreas: Set<string> }

/** Bereichs-Verzeichnis plus die nie vergebbaren Bereiche/Tools (Quelle: Backend, `tool_pools.check_item`). */
export function useAreaCatalog(): { catalog: AreaCatalog | null; error: boolean } {
  const { i18n } = useTranslation()
  const lang = i18n.language?.startsWith("en") ? "en" : "de"
  const [catalog, setCatalog] = useState<AreaCatalog | null>(null)
  const [error, setError] = useState(false)
  useEffect(() => {
    let alive = true
    Promise.all([
      api.get<{ groups: AreaGroup[]; areas: AreaInfo[]; unassigned: string[] }>(`/agent-areas?lang=${lang}`),
      api.get<{ areas: string[]; tools: string[] }>("/agent-areas/never"),
    ]).then(([a, n]) => {
      if (alive) setCatalog({ ...a, never: new Set(n.tools), neverAreas: new Set(n.areas) })
    }).catch(() => { if (alive) setError(true) })
    return () => { alive = false }
  }, [lang])
  return { catalog, error }
}
