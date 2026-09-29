export type UserRole = "admin" | "user"

export interface User {
  user_id: string
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
