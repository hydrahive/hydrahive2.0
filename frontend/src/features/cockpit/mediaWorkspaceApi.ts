import { api } from "@/shared/api-client"

export interface MediaShot { id: string; title: string; description: string; duration: number; camera: string; character_ids: string[]; asset_ids: string[]; dialogue: string }
export interface MediaScene { id: string; title: string; description: string; shots: MediaShot[] }
export interface MediaAct { id: string; title: string; scenes: MediaScene[] }
export interface MediaScreenplay { version?: number; title: string; logline: string; acts: MediaAct[]; updated_at?: string | null }
export interface MediaAgentContext { version?: number; note: string; active_scene_id: string | null; asset_ids: string[]; prompt_draft: string; updated_at?: string | null }
export type MediaTrackKind = "video" | "voice" | "music" | "audio"
export interface MediaTimelineClip { id: string; asset_id: string; start: number; duration: number; source_in: number; volume: number }
export interface MediaTimelineTrack { id: string; name: string; kind: MediaTrackKind; muted: boolean; clips: MediaTimelineClip[] }
export interface MediaTimeline { version?: number; fps: number; width: number; height: number; tracks: MediaTimelineTrack[]; updated_at?: string | null }

const base = (projectId: string, mediaSlug: string) => `/projects/${projectId}/media-projects/${mediaSlug}`
export const mediaWorkspaceApi = {
  getScreenplay: (projectId: string, mediaSlug: string) => api.get<MediaScreenplay>(`${base(projectId, mediaSlug)}/screenplay`),
  saveScreenplay: (projectId: string, mediaSlug: string, value: MediaScreenplay) => api.put<MediaScreenplay>(`${base(projectId, mediaSlug)}/screenplay`, value),
  getAgentContext: (projectId: string, mediaSlug: string) => api.get<MediaAgentContext>(`${base(projectId, mediaSlug)}/agent-context`),
  saveAgentContext: (projectId: string, mediaSlug: string, value: MediaAgentContext) => api.put<MediaAgentContext>(`${base(projectId, mediaSlug)}/agent-context`, value),
  getTimeline: (projectId: string, mediaSlug: string) => api.get<MediaTimeline>(`${base(projectId, mediaSlug)}/timeline`),
  saveTimeline: (projectId: string, mediaSlug: string, value: MediaTimeline) => api.put<MediaTimeline>(`${base(projectId, mediaSlug)}/timeline`, value),
}
