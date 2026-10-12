import i18n from "@/i18n"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { useVaultStore, VAULT_401_CODES } from "@/features/vault/vaultStore"

interface CodedDetail {
  code: string
  params?: Record<string, unknown>
}

function isCoded(detail: unknown): detail is CodedDetail {
  return typeof detail === "object" && detail !== null && "code" in detail && typeof (detail as CodedDetail).code === "string"
}

export function buildErrorMessage(body: { detail?: unknown }, status: number): string {
  if (isCoded(body.detail)) {
    const { code, params } = body.detail
    const key = `errors:${code}`
    const translated = i18n.t(key, { ...(params ?? {}), defaultValue: code })
    return translated
  }
  if (typeof body.detail === "string") return body.detail
  return `HTTP ${status}`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = useAuthStore.getState().token
  const vaultToken = useVaultStore.getState().token
  const isFormData = init?.body instanceof FormData
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(vaultToken ? { "X-HH-Vault": vaultToken } : {}),
      ...init?.headers,
    },
  })

  // Vault (docs/specs/vault.md §4.3): gleitende Sperre → verlängerten Token übernehmen.
  const refreshed = res.headers.get("X-HH-Vault-Refresh")
  if (refreshed) useVaultStore.getState().setToken(refreshed)

  if (res.status === 401) {
    const body = await res.clone().json().catch(() => ({}))
    const code = isCoded(body.detail) ? body.detail.code : ""
    if (!VAULT_401_CODES.has(code)) {
      useAuthStore.getState().logout()
      throw new Error(i18n.t("errors:not_authenticated", { defaultValue: "Not authenticated" }))
    }
  }
  if (res.status === 204) return undefined as T
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    if (res.status === 423 && isCoded(body.detail) && body.detail.code === "vault_locked") {
      useVaultStore.getState().setToken(null)
      useVaultStore.getState().requestUnlock(body.detail.params?.pin_set !== false)
    }
    const err = new Error(buildErrorMessage(body, res.status)) as Error & { status?: number; code?: string }
    err.status = res.status
    err.code = isCoded(body.detail) ? body.detail.code : undefined
    throw err
  }
  return res.json()
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  postForm: <T>(path: string, form: FormData) =>
    request<T>(path, { method: "POST", body: form }),
}
