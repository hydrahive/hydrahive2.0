import i18n from "@/i18n"
import { useAuthStore } from "@/features/auth/useAuthStore"

interface CodedDetail {
  code: string
  params?: Record<string, unknown>
}

function isCoded(detail: unknown): detail is CodedDetail {
  return typeof detail === "object" && detail !== null && "code" in detail && typeof (detail as CodedDetail).code === "string"
}

function buildErrorMessage(body: { detail?: unknown }, status: number): string {
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
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  })

  if (res.status === 401) {
    useAuthStore.getState().logout()
    throw new Error(i18n.t("errors:not_authenticated", { defaultValue: "Not authenticated" }))
  }
  if (res.status === 204) return undefined as T
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(buildErrorMessage(body, res.status))
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
}
