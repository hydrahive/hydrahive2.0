import { api } from "@/shared/api-client"

// ─── Forschungs-APIs (Admin) ──────────────────────────────────────────────
// Core-Kernel: Auth-Injektions-Registry für das fetch_url-Tool. Bewusst NICHT
// im Akte/Health-Modul (research bleibt Core).

export type ResearchCategory = "literatur" | "medikamente" | "krankheiten_gene" | "studien"

export interface ResearchApiPublic {
  id: string
  name: string
  category: ResearchCategory
  base_url: string
  url_pattern: string
  docs_url: string
  description: string
  needs_key: boolean
  auth_type: "none" | "query" | "header" | "bearer"
  auth_param: string
  polite_email_param: string
  rate_limit: string
  enabled: boolean
  has_key: boolean
}

export interface ResearchTestResult {
  ok: boolean
  status?: number
  error?: string
}

export const researchApi = {
  list: () => api.get<{ apis: ResearchApiPublic[] }>("/research-apis"),
  update: (id: string, body: { enabled?: boolean; key?: string }) =>
    api.patch<ResearchApiPublic>(`/research-apis/${id}`, body),
  test: (id: string) =>
    api.post<ResearchTestResult>(`/research-apis/${id}/test`, {}),
}
