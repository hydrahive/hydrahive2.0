import { api } from "@/shared/api-client"

export interface VaultStatus {
  pin_set: boolean
  unlocked: boolean
  remaining_seconds: number
  idle_seconds: number
}

export const vaultApi = {
  status: () => api.get<VaultStatus>("/vault/status"),
  setup: (password: string, pin: string) => api.post<{ vault_token: string }>("/vault/setup", { password, pin }),
  unlock: (pin: string) => api.post<{ vault_token: string }>("/vault/unlock", { pin }),
  lock: () => api.post<{ ok: boolean }>("/vault/lock", {}),
  reset: (password: string, pin: string) => api.post<{ vault_token: string }>("/vault/reset", { password, pin }),
  adminReset: (userId: string) => api.post<{ ok: boolean }>(`/vault/admin/reset/${encodeURIComponent(userId)}`, {}),
}

/** 6–12 Ziffern (wie Backend vault/pins.py). */
export function pinValid(pin: string): boolean {
  return /^[0-9]{6,12}$/.test(pin)
}
