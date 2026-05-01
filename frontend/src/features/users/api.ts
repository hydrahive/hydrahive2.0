import { api } from "@/shared/api-client"
import type { User, UserRole } from "./types"

export interface UserPatch {
  role?: UserRole
}

export const usersApi = {
  list: () => api.get<User[]>("/users"),
  create: (username: string, password: string, role: UserRole) =>
    api.post<User>("/users", { username, password, role }),
  update: (username: string, patch: UserPatch) =>
    api.patch<{ ok: boolean }>(`/users/${encodeURIComponent(username)}`, patch),
  delete: (username: string) => api.delete<void>(`/users/${encodeURIComponent(username)}`),
  changePassword: (username: string, new_password: string) =>
    api.patch<{ ok: boolean }>(`/users/${encodeURIComponent(username)}/password`, { new_password }),
}
