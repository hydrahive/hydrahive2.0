import { api } from "@/shared/api-client"

export interface MediaProject {
  version: number
  slug: string
  name: string
  description: string
  project_id: string
  created_at: string
  updated_at: string
}

export const mediaProjectsApi = {
  list: (projectId: string) => api.get<MediaProject[]>(`/projects/${projectId}/media-projects`),
  create: (projectId: string, input: { slug: string; name: string; description: string }) =>
    api.post<MediaProject>(`/projects/${projectId}/media-projects`, input),
  update: (projectId: string, slug: string, input: Partial<Pick<MediaProject, "name" | "description">>) =>
    api.patch<MediaProject>(`/projects/${projectId}/media-projects/${slug}`, input),
  remove: (projectId: string, slug: string) =>
    api.delete<void>(`/projects/${projectId}/media-projects/${slug}`),
}
