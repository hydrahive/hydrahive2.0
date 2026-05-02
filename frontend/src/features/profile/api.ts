import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"

export const profileApi = {
  changeOwnPassword: (new_password: string) =>
    api.patch<{ ok: boolean }>("/users/me/password", { new_password }),

  downloadBackup: () => {
    const token = useAuthStore.getState().token ?? ""
    return fetch("/api/users/me/backup", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    })
  },

  restoreBackup: (file: File) => {
    const token = useAuthStore.getState().token ?? ""
    const form = new FormData()
    form.append("archive", file)
    return fetch("/api/users/me/restore", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    }).then((r) => (r.ok ? r.json() : r.json().then((e) => Promise.reject(e))))
  },
}
