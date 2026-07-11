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

export type MediaPromptType = "general" | "image" | "video" | "music" | "voice" | "storyboard"
export type MediaPromptStatus = "draft" | "executed" | "archived"

export interface MediaPrompt {
  version: number
  slug: string
  type: MediaPromptType
  title: string
  status: MediaPromptStatus
  model: string
  asset_refs: string[]
  result_refs: string[]
  created_at: string
  updated_at: string
  body: string
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

const promptBase = (projectId: string, mediaSlug: string) => `/projects/${projectId}/media-projects/${mediaSlug}/prompts`

export const mediaPromptsApi = {
  list: (projectId: string, mediaSlug: string) => api.get<MediaPrompt[]>(promptBase(projectId, mediaSlug)),
  create: (projectId: string, mediaSlug: string, input: { slug: string; type: MediaPromptType; title: string; body: string; model: string; asset_refs: string[] }) =>
    api.post<MediaPrompt>(promptBase(projectId, mediaSlug), input),
  update: (projectId: string, mediaSlug: string, type: MediaPromptType, slug: string, input: Partial<Pick<MediaPrompt, "title" | "body" | "model" | "status" | "asset_refs" | "result_refs">>) =>
    api.patch<MediaPrompt>(`${promptBase(projectId, mediaSlug)}/${type}/${slug}`, input),
  remove: (projectId: string, mediaSlug: string, type: MediaPromptType, slug: string) =>
    api.delete<void>(`${promptBase(projectId, mediaSlug)}/${type}/${slug}`),
}
