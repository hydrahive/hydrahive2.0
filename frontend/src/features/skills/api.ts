import { api } from "@/shared/api-client"
import type { Skill, SkillSavePayload, SkillScope } from "./types"

export const skillsApi = {
  /** Wenn agentId gesetzt: gemergte Liste (system+user+agent). Sonst: scope-basiert. */
  list: (params?: { agentId?: string; scope?: SkillScope | "all" }) => {
    const qs = new URLSearchParams()
    if (params?.agentId) qs.set("agent_id", params.agentId)
    if (params?.scope) qs.set("scope", params.scope)
    const q = qs.toString()
    return api.get<Skill[]>(`/skills${q ? "?" + q : ""}`)
  },
  get: (scope: SkillScope, name: string, owner?: string) => {
    const qs = owner ? `?owner=${encodeURIComponent(owner)}` : ""
    return api.get<Skill>(`/skills/${scope}/${encodeURIComponent(name)}${qs}`)
  },
  save: (scope: SkillScope, payload: SkillSavePayload, owner?: string) => {
    const qs = owner ? `?owner=${encodeURIComponent(owner)}` : ""
    return api.post<Skill>(`/skills/${scope}${qs}`, payload)
  },
  remove: (scope: SkillScope, name: string, owner?: string) => {
    const qs = owner ? `?owner=${encodeURIComponent(owner)}` : ""
    return api.delete<void>(`/skills/${scope}/${encodeURIComponent(name)}${qs}`)
  },
}
