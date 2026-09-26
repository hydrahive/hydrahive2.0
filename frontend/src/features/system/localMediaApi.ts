import { api } from "@/shared/api-client"

export type LocalMediaBlockReason = "no_gpu" | "vram_too_small" | "disk_too_small"

export interface LocalMediaStatus {
  installed: boolean
  can_install: boolean
  can_uninstall: boolean
  blocked_reason: LocalMediaBlockReason | null
  gpu: { name: string; vram_mib: number } | null
  min_vram_mib: number
  free_bytes: number
  min_free_bytes: number
  download_bytes: number
  running: boolean
}

export const localMediaApi = {
  status: () => api.get<LocalMediaStatus>("/system/local-media/status"),
  install: () => api.post<{ started: boolean }>("/system/local-media/install", {}),
  uninstall: () => api.post<{ started: boolean }>("/system/local-media/uninstall", {}),
  log: (tail = 300) => api.get<{ lines: string[]; exists: boolean }>(`/system/local-media/log?tail=${tail}`),
}

/** Das Log einer Aktion endet mit genau einer dieser Zeilen (installer/local-media-ctl.sh). */
export function actionOutcome(lines: string[]): "ok" | "failed" | null {
  for (let i = lines.length - 1; i >= 0; i--) {
    if (lines[i].includes("===== ")) return null
    if (lines[i].includes("[hh2-media] FERTIG:")) return "ok"
    if (lines[i].includes("[hh2-media] FEHLER:")) return "failed"
  }
  return null
}

export function gib(bytes: number): string {
  return `${Math.round(bytes / 1024 ** 3)} GB`
}
