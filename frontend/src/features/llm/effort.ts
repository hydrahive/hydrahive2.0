import { useEffect, useState } from "react"
import { api } from "@/shared/api-client"

/** SSOT für die erweiterte Effort-Capability (xhigh/max): die Modell-Präfixe
 *  kommen vom Backend (/llm/effort-models → EFFORT_PARAM_MODELS), damit die
 *  Liste nicht im Frontend dupliziert und bei neuen Modellen vergessen wird (#214). */

let cache: string[] | null = null
let inflight: Promise<string[]> | null = null

export async function fetchEffortPrefixes(): Promise<string[]> {
  if (cache) return cache
  if (!inflight) {
    inflight = api
      .get<{ prefixes: string[] }>("/llm/effort-models")
      .then((r) => {
        cache = r.prefixes
        return r.prefixes
      })
      .catch(() => {
        inflight = null
        return []
      })
  }
  return inflight
}

export function modelSupportsExtendedEffort(model: string, prefixes: string[]): boolean {
  const bare = model.replace(/^anthropic\//, "")
  return prefixes.some((p) => bare.startsWith(p))
}

/** Cached Hook — fetcht die Präfixe einmal und gibt sie an die Komponenten. */
export function useEffortPrefixes(): string[] {
  const [prefixes, setPrefixes] = useState<string[]>(cache ?? [])
  useEffect(() => {
    let active = true
    fetchEffortPrefixes().then((p) => {
      if (active) setPrefixes(p)
    })
    return () => {
      active = false
    }
  }, [])
  return prefixes
}
