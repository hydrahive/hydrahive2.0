export type SkillScope = "system" | "user" | "agent"

export interface SkillSource {
  url: string
  auth: string
  description: string
}

export interface Skill {
  name: string
  description: string
  when_to_use: string
  tools_required: string[]
  sources: SkillSource[]
  body: string
  scope: SkillScope
  owner: string
}

export interface SkillSavePayload {
  name: string
  description: string
  when_to_use: string
  tools_required: string[]
  sources: SkillSource[]
  body: string
}
