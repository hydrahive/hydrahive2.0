export type AccessLevel = "use" | "manage"
export type SubjectType = "user" | "group" | "everyone"

export interface CapabilityGrant {
  subject_type: SubjectType
  subject_id: string
  level: AccessLevel
}

export interface CatalogCapability {
  id: string
  label: string
  default: "everyone" | "admin_only"
  module_id: string
  tools: string[]
  grants: CapabilityGrant[]
}

export interface AccessGroup {
  id: string
  name: string
  description?: string
  member_count?: number
}

export interface AccessGroupDetail extends AccessGroup {
  members: { user_id: string; username: string }[]
}

export interface AccessUser {
  user_id: string
  username: string
  role: string
}

export interface AccessCatalog {
  capabilities: CatalogCapability[]
  groups: AccessGroup[]
  users: AccessUser[]
}

export interface MyAccess {
  admin: boolean
  capabilities: Record<string, AccessLevel>
  declared: string[]
  groups: { id: string; name: string }[]
}
