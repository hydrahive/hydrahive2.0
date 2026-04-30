import { useEffect, useState } from "react"
import type { RegistryMeta, SpecMeta } from "./types"
import { butlerApi } from "./api"

export function useRegistry() {
  const [registry, setRegistry] = useState<RegistryMeta | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    butlerApi.registry()
      .then((r) => { if (alive) setRegistry(r) })
      .catch((e) => { if (alive) setError(e instanceof Error ? e.message : String(e)) })
    return () => { alive = false }
  }, [])

  return { registry, error }
}

export function findSpec(reg: RegistryMeta | null, type: string, subtype: string): SpecMeta | null {
  if (!reg) return null
  const list = type === "trigger" ? reg.triggers
    : type === "condition" ? reg.conditions
    : type === "action" ? reg.actions
    : []
  return list.find((s) => s.subtype === subtype) ?? null
}
