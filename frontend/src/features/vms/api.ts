import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"
import type { ImportJob, ISO, Snapshot, VM, VMCreateInput } from "./types"

export const vmsApi = {
  list: () => api.get<VM[]>("/vms"),
  get: (id: string) => api.get<VM>(`/vms/${id}`),
  create: (input: VMCreateInput) => api.post<VM>("/vms", input),
  remove: (id: string) => api.delete<void>(`/vms/${id}`),
  start: (id: string) => api.post<VM>(`/vms/${id}/start`, {}),
  stop: (id: string) => api.post<VM>(`/vms/${id}/stop`, {}),
  poweroff: (id: string) => api.post<VM>(`/vms/${id}/poweroff`, {}),
  vncInfo: (id: string) => api.get<{ token: string; ws_path: string }>(`/vms/${id}/vnc`),
  stats: (id: string) => api.get<{ alive: boolean; cpu_pct: number; rss_mb: number; uptime_s: number }>(`/vms/${id}/stats`),
  log: (id: string, tail = 200) => api.get<{ lines: string[]; exists: boolean }>(`/vms/${id}/log?tail=${tail}`),
  listSnapshots: (id: string) => api.get<Snapshot[]>(`/vms/${id}/snapshots`),
  createSnapshot: (id: string, name: string, description?: string) =>
    api.post<Snapshot>(`/vms/${id}/snapshots`, { name, description }),
  restoreSnapshot: (id: string, snapId: string) =>
    api.post<void>(`/vms/${id}/snapshots/${snapId}/restore`, {}),
  deleteSnapshot: (id: string, snapId: string) =>
    api.delete<void>(`/vms/${id}/snapshots/${snapId}`),
  isos: () => api.get<ISO[]>("/vms/isos/list"),
  isoDelete: (filename: string) => api.delete<void>(`/vms/isos/${encodeURIComponent(filename)}`),
  importJobs: () => api.get<ImportJob[]>("/vms/import-jobs"),
  importFromPath: (path: string) => api.post<{ job_id: string }>("/vms/import-jobs/from-path", { source_path: path }),
  importJobDelete: (jobId: string) => api.delete<void>(`/vms/import-jobs/${jobId}`),
}

export async function uploadImport(file: File, onProgress?: (pct: number) => void): Promise<{ job_id: string }> {
  const token = useAuthStore.getState().token ?? ""
  return await new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const form = new FormData()
    form.append("disk", file)
    xhr.open("POST", "/api/vms/import-jobs/upload")
    xhr.setRequestHeader("Authorization", `Bearer ${token}`)
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100))
    }
    xhr.onload = () => {
      if (xhr.status === 202) {
        try { resolve(JSON.parse(xhr.responseText)) } catch (e) { reject(e) }
      } else {
        reject(new Error(xhr.responseText || `${xhr.status}`))
      }
    }
    xhr.onerror = () => reject(new Error("Network error"))
    xhr.send(form)
  })
}

export async function uploadIso(file: File, onProgress?: (pct: number) => void): Promise<ISO> {
  const token = useAuthStore.getState().token ?? ""
  // XHR statt fetch — nur XHR liefert Upload-Progress.
  return await new Promise<ISO>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const form = new FormData()
    form.append("iso", file)
    xhr.open("POST", "/api/vms/isos/upload")
    xhr.setRequestHeader("Authorization", `Bearer ${token}`)
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    }
    xhr.onload = () => {
      if (xhr.status === 201) {
        try { resolve(JSON.parse(xhr.responseText)) }
        catch (e) { reject(e) }
      } else {
        reject(new Error(xhr.responseText || `${xhr.status}`))
      }
    }
    xhr.onerror = () => reject(new Error("Network error"))
    xhr.send(form)
  })
}
