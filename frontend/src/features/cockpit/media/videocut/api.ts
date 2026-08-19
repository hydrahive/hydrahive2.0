import { fileUrl } from "@/shared/files"
import { loadMediaLibrary, resolveMediaRoot, type MediaLibraryItem } from "../mediaRegistry"
import { mediaAssetsApi, mediaProjectsApi, type MediaAssetReference } from "../../mediaProjectsApi"
import { mediaWorkspaceApi, type MediaTimeline } from "../../mediaWorkspaceApi"

/** Media-Projekt-Slug für den Videoschnitt — wird still angelegt. */
export const CUT_SLUG = "schnitt"

/** Bibliothekseintrag, normalisiert über alle Medienquellen.
 *
 *  Die Form kommt aus der Modul-Registry; der Core kennt keine Modul-Rohtypen
 *  mehr. Re-Export unter dem etablierten Namen, damit bestehende Importe
 *  (ClipLibrary, TrackArea, InputMonitor …) unverändert bleiben. */
export type LibraryItem = MediaLibraryItem

export function libraryFileUrl(absPath: string): string {
  return fileUrl(absPath)
}

/** Auflösbares Medium eines Timeline-Clips (für Playback). */
export interface ClipMedia {
  url: string
  kind: "video" | "image" | "audio"
}

/** Baut asset_id → abspielbare URL/Art aus Asset-Referenzen + Atelier-Root.
 *  rel_path liegt als `atelier/<rel>` vor; der absolute Pfad ergibt sich aus
 *  dem Atelier-Root des Projekts, ausgeliefert über /api/files. */
export function buildAssetMedia(
  assets: MediaAssetReference[],
  atelierRoot: string | null,
): Map<string, ClipMedia> {
  const map = new Map<string, ClipMedia>()
  if (!atelierRoot) return map
  for (const asset of assets) {
    const rel = asset.rel_path.startsWith("atelier/") ? asset.rel_path.slice("atelier/".length) : asset.rel_path
    const kind = asset.kind === "video" ? "video" : asset.kind === "image" ? "image" : "audio"
    map.set(asset.id, { url: fileUrl(`${atelierRoot}/${rel}`), kind })
  }
  return map
}

/** Projekt-Root für absolute Pfade, über die registrierten Medienquellen.
 *  Keine Quelle installiert oder Fehler → null. */
export async function loadAtelierRoot(projectId: string): Promise<string | null> {
  return resolveMediaRoot(projectId)
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

/** Lädt die Bibliothek aller registrierten Medienquellen.
 *  Ohne installierte Quelle → leere Liste (kein Fehler). */
export async function loadLibrary(projectId: string, atelierRoot: string | null): Promise<LibraryItem[]> {
  return loadMediaLibrary(projectId, atelierRoot)
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
