import { atelierApi, fileUrl } from "@/modules/atelier/api"
import type { AudioLibraryItem, GalleryItem, VideoJob } from "@/modules/atelier/types"
import { mediaAssetsApi, mediaProjectsApi, type MediaAssetReference } from "../../mediaProjectsApi"
import { mediaWorkspaceApi, type MediaTimeline } from "../../mediaWorkspaceApi"

/** Media-Projekt-Slug für den Videoschnitt — wird still angelegt. */
export const CUT_SLUG = "schnitt"

/** Bibliothekseintrag, normalisiert über alle Atelier-Quellen. */
export interface LibraryItem {
  key: string
  kind: "video" | "image" | "audio"
  label: string
  /** rel_path im Projekt-Workspace (atelier/...) für Asset-Referenzen. */
  relPath: string
  /** Absoluter Pfad für Thumbnails/Preview via /api/files. */
  absPath: string | null
  /** Bekannte Dauer in Sekunden (Videos aus Job-Meta), sonst null. */
  duration: number | null
}

export function libraryFileUrl(absPath: string): string {
  return fileUrl(absPath)
}

/** Stellt sicher, dass das Schnitt-Media-Projekt existiert. */
export async function ensureCutProject(projectId: string): Promise<void> {
  const existing = await mediaProjectsApi.list(projectId)
  if (existing.some((item) => item.slug === CUT_SLUG)) return
  await mediaProjectsApi.create(projectId, {
    slug: CUT_SLUG,
    name: "Videoschnitt",
    description: "Automatisch angelegt für die Nachbearbeitung im Media-Cockpit.",
  })
}

/** Lädt alle Bibliotheksquellen des Projekts parallel. Fehler je Quelle → leere Liste. */
export async function loadLibrary(projectId: string, atelierRoot: string | null): Promise<LibraryItem[]> {
  const [gallery, videos, audio] = await Promise.allSettled([
    atelierApi.gallery(projectId),
    atelierApi.listVideos(projectId),
    atelierApi.audioLibrary(projectId),
  ])
  const items: LibraryItem[] = []

  if (videos.status === "fulfilled") {
    for (const job of videos.value as VideoJob[]) {
      if (job.status !== "completed" || !job.video_rel) continue
      items.push({
        key: `video:${job.video_rel}`,
        kind: "video",
        label: job.prompt?.slice(0, 60) || job.video_rel.split("/").pop() || job.job_id,
        relPath: `atelier/${job.video_rel}`,
        absPath: atelierRoot ? `${atelierRoot}/${job.video_rel}` : null,
        duration: job.duration > 0 ? job.duration : null,
      })
    }
  }
  if (gallery.status === "fulfilled") {
    for (const img of gallery.value as GalleryItem[]) {
      items.push({
        key: `image:${img.rel}`,
        kind: "image",
        label: img.name,
        relPath: `atelier/${img.rel}`,
        absPath: img.path || null,
        duration: null,
      })
    }
  }
  if (audio.status === "fulfilled") {
    for (const track of audio.value as AudioLibraryItem[]) {
      items.push({
        key: `audio:${track.rel}`,
        kind: "audio",
        label: track.name,
        relPath: `atelier/${track.rel}`,
        absPath: atelierRoot ? `${atelierRoot}/${track.rel}` : null,
        duration: null,
      })
    }
  }
  return items
}

/** Findet oder erstellt die Asset-Referenz für einen Bibliothekseintrag. */
export async function ensureAssetRef(
  projectId: string,
  item: LibraryItem,
  existing: MediaAssetReference[],
): Promise<MediaAssetReference> {
  const found = existing.find((a) => a.rel_path === item.relPath && a.source_project_id === projectId)
  if (found) return found
  const kind = item.kind === "video" ? "video" : item.kind === "image" ? "image" : "audio"
  const id = `${kind}-${hashString(item.relPath)}`
  return mediaAssetsApi.create(projectId, CUT_SLUG, {
    id,
    kind,
    label: item.label.slice(0, 100),
    source_project_id: projectId,
    rel_path: item.relPath,
  })
}

export async function loadTimelineAndAssets(projectId: string): Promise<{ timeline: MediaTimeline; assets: MediaAssetReference[] }> {
  const [timeline, assets] = await Promise.all([
    mediaWorkspaceApi.getTimeline(projectId, CUT_SLUG),
    mediaAssetsApi.list(projectId, CUT_SLUG),
  ])
  return { timeline, assets }
}

export function saveTimeline(projectId: string, timeline: MediaTimeline): Promise<MediaTimeline> {
  return mediaWorkspaceApi.saveTimeline(projectId, CUT_SLUG, timeline)
}

/** Kurzer stabiler Hash für Asset-IDs (djb2). */
function hashString(value: string): string {
  let hash = 5381
  for (let i = 0; i < value.length; i++) hash = ((hash << 5) + hash + value.charCodeAt(i)) >>> 0
  return hash.toString(36)
}
