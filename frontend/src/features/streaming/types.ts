export interface StreamingCredentials {
  username: string
  plex_path: string
  has_password: boolean
}

export interface Episode {
  key: string
  episode: number
  bunny_video_id: string
  bunny_library_id: string
  bunny_video_type: string
}

export interface ScrapeResult {
  title: string
  season: number
  episodes: Episode[]
}

export interface StreamingJob {
  id: string
  series_title: string
  season: number
  episode: number
  episode_key: string
  output_path: string
  status: "pending" | "downloading" | "done" | "error" | "skipped"
  progress: number
  error: string | null
  created_at: string
}
