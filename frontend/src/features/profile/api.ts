import { api } from "@/shared/api-client"

export const profileApi = {
  changeOwnPassword: (new_password: string) =>
    api.patch<{ ok: boolean }>("/users/me/password", { new_password }),
}
