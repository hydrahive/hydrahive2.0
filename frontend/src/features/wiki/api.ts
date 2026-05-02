import { useAuthStore } from "@/features/auth/useAuthStore"
import type { WikiPage, WikiPageIn } from "./types"

function headers() {
  return { "Content-Type": "application/json", Authorization: `Bearer ${useAuthStore.getState().token}` }
}

export const wikiApi = {
  list: (q?: string): Promise<WikiPage[]> => {
    const url = q ? `/api/wiki?q=${encodeURIComponent(q)}` : "/api/wiki"
    return fetch(url, { headers: headers() }).then((r) => r.json())
  },
  get: (slug: string): Promise<WikiPage> =>
    fetch(`/api/wiki/${slug}`, { headers: headers() }).then((r) => r.json()),
  create: (data: WikiPageIn): Promise<WikiPage> =>
    fetch("/api/wiki", { method: "POST", headers: headers(), body: JSON.stringify(data) }).then((r) => r.json()),
  update: (slug: string, data: WikiPageIn): Promise<WikiPage> =>
    fetch(`/api/wiki/${slug}`, { method: "PUT", headers: headers(), body: JSON.stringify(data) }).then((r) => r.json()),
  delete: (slug: string): Promise<void> =>
    fetch(`/api/wiki/${slug}`, { method: "DELETE", headers: headers() }).then(() => undefined),
}
