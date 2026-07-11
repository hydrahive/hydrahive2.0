import { useEffect, useState } from "react"
import { api } from "@/shared/api-client"

const cache = new Map<string, string[]>()

export async function fetchEffortLevels(model: string): Promise<string[]> {
  if (!model) return []
  const cached = cache.get(model)
  if (cached) return cached
  try {
    const response = await api.get<{ levels: string[] }>(`/llm/effort-levels?model=${encodeURIComponent(model)}`)
    cache.set(model, response.levels)
    return response.levels
  } catch {
    return []
  }
}

export function useEffortLevels(model: string): string[] {
  const [levels, setLevels] = useState<string[]>(cache.get(model) ?? [])
  useEffect(() => {
    let active = true
    setLevels(cache.get(model) ?? [])
    fetchEffortLevels(model).then((values) => { if (active) setLevels(values) })
    return () => { active = false }
  }, [model])
  return levels
}
