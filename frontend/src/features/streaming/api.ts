import { api } from "@/shared/api-client"
import type { ScrapeResult, StreamingCredentials, StreamingJob } from "./types"

export const streamingApi = {
  getCredentials: (): Promise<StreamingCredentials | null> =>
    api.get("/streaming/credentials"),

  saveCredentials: (username: string, password: string, plex_path: string): Promise<void> =>
    api.put("/streaming/credentials", { username, password, plex_path }),

  scrape: (url: string): Promise<ScrapeResult> =>
    api.post("/streaming/scrape", { url }),

  startDownload: (body: {
    series_title: string
    series_url: string
    season: number
    plex_path: string
    jobs: { episode_key: string; episode: number; bunny_video_id: string; bunny_library_id: string }[]
  }): Promise<{ job_ids: string[] }> =>
    api.post("/streaming/download/start", body),

  listJobs: (): Promise<StreamingJob[]> =>
    api.get("/streaming/jobs"),

  deleteJob: (job_id: string): Promise<void> =>
    api.delete(`/streaming/jobs/${job_id}`),

  cancelJob: (job_id: string): Promise<void> =>
    api.post(`/streaming/jobs/${job_id}/cancel`, {}),
}
