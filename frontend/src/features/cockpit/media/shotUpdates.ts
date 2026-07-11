import type { MediaScreenplay, MediaShot } from "../mediaWorkspaceApi"

export function updateShot(
  screenplay: MediaScreenplay,
  actIndex: number,
  sceneIndex: number,
  shotIndex: number,
  changes: Partial<MediaShot>,
): MediaScreenplay {
  return {
    ...screenplay,
    acts: screenplay.acts.map((act, ai) => ai !== actIndex ? act : {
      ...act,
      scenes: act.scenes.map((scene, si) => si !== sceneIndex ? scene : {
        ...scene,
        shots: scene.shots.map((shot, hi) => hi === shotIndex ? { ...shot, ...changes } : shot),
      }),
    }),
  }
}

export function toggleReference(ids: string[], id: string): string[] {
  return ids.includes(id) ? ids.filter((value) => value !== id) : [...ids, id]
}

export function clampDuration(value: number): number {
  if (!Number.isFinite(value)) return 5
  return Math.min(3600, Math.max(0.1, value))
}
