export type SkillScope = "system" | "user" | "agent"

export interface Skill {
  name: string
  description: string
  when_to_use: string
  tools_required: string[]
  body: string
  scope: SkillScope
  owner: string
}

export interface SkillSavePayload {
  name: string
  description: string
  when_to_use: string
  tools_required: string[]
  body: string
}
