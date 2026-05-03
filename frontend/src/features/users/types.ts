export type UserRole = "admin" | "user"

export interface User {
  username: string
  role: UserRole
}

export interface ApiKey {
  id: string
  name: string
  username: string
  role: UserRole
  created_at: string
}
