import { api } from "@/shared/api-client"

export const profileApi = {
  changeOwnPassword: (new_password: string) =>
    api.patch<{ ok: boolean }>("/users/me/password", { new_password }),

  downloadBackup: () =>
    fetch("/api/users/me/backup", {
      method: "POST",
      headers: { Authorization: `Bearer ${localStorage.getItem("hh_token") ?? ""}` },
    }),

  restoreBackup: (file: File) => {
    const form = new FormData()
    form.append("archive", file)
    return fetch("/api/users/me/restore", {
      method: "POST",
      headers: { Authorization: `Bearer ${localStorage.getItem("hh_token") ?? ""}` },
      body: form,
    }).then((r) => (r.ok ? r.json() : r.json().then((e) => Promise.reject(e))))
  },
}
