import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"
import type { ISO, VM, VMCreateInput } from "./types"

export const vmsApi = {
  list: () => api.get<VM[]>("/vms"),
  get: (id: string) => api.get<VM>(`/vms/${id}`),
  create: (input: VMCreateInput) => api.post<VM>("/vms", input),
  remove: (id: string) => api.delete<void>(`/vms/${id}`),
  start: (id: string) => api.post<VM>(`/vms/${id}/start`, {}),
  stop: (id: string) => api.post<VM>(`/vms/${id}/stop`, {}),
  poweroff: (id: string) => api.post<VM>(`/vms/${id}/poweroff`, {}),
  isos: () => api.get<ISO[]>("/vms/isos/list"),
  isoDelete: (filename: string) => api.delete<void>(`/vms/isos/${encodeURIComponent(filename)}`),
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
