import { api } from "@/shared/api-client"
import type { AccessCatalog, AccessGroup, AccessGroupDetail, AccessLevel, MyAccess, SubjectType } from "./types"

export const accessApi = {
  me: () => api.get<MyAccess>("/access/me"),
  catalog: () => api.get<AccessCatalog>("/access/capabilities"),
  grant: (capability: string, subject_type: SubjectType, subject_id: string, level: AccessLevel) =>
    api.put<void>("/access/grants", { capability, subject_type, subject_id, level }),
  revoke: (capability: string, subject_type: SubjectType, subject_id: string) =>
    api.delete<void>(`/access/grants?${new URLSearchParams({ capability, subject_type, subject_id })}`),
  groups: () => api.get<AccessGroup[]>("/access/groups"),
  group: (id: string) => api.get<AccessGroupDetail>(`/access/groups/${encodeURIComponent(id)}`),
  createGroup: (name: string, description: string) =>
    api.post<AccessGroupDetail>("/access/groups", { name, description }),
  updateGroup: (id: string, patch: { name?: string; description?: string }) =>
    api.patch<AccessGroupDetail>(`/access/groups/${encodeURIComponent(id)}`, patch),
  deleteGroup: (id: string) => api.delete<void>(`/access/groups/${encodeURIComponent(id)}`),
  addMember: (id: string, userId: string) =>
    api.put<void>(`/access/groups/${encodeURIComponent(id)}/members/${encodeURIComponent(userId)}`, {}),
  removeMember: (id: string, userId: string) =>
    api.delete<void>(`/access/groups/${encodeURIComponent(id)}/members/${encodeURIComponent(userId)}`),
}
