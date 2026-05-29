import { api } from "@/shared/api-client"

export interface MetricDay {
  date: string
  value: number
}

export interface MetricSummary {
  latest: number
  trend: string
  unit: string
  days: MetricDay[]
}

export interface MetricsSummary {
  metrics: Record<string, MetricSummary>
  last_ingest: string | null
  period_days: number
}

export interface IngestRecord {
  id: string
  received_at: string
  automation_name: string | null
  automation_id: string | null
  session_id: string | null
  period: string | null
  aggregation: string | null
}

export interface IngestRecordDetail extends IngestRecord {
  payload: Record<string, unknown>
}

export const healthApi = {
  metrics(days = 7, metric?: string): Promise<MetricsSummary> {
    const params = new URLSearchParams({ days: String(days) })
    if (metric) params.set("metric", metric)
    return api.get<MetricsSummary>(`/health-data/metrics?${params}`)
  },

  list(limit = 50): Promise<{ records: IngestRecord[]; count: number }> {
    return api.get<{ records: IngestRecord[]; count: number }>(
      `/health-data/data?limit=${limit}`
    )
  },

  detail(id: string): Promise<{ id: string; payload: Record<string, unknown> }> {
    return api.get<{ id: string; payload: Record<string, unknown> }>(
      `/health-data/data/${id}`
    )
  },
}

// ─── TK eGA (nativ) ───────────────────────────────────────────────────────

export interface EgaImportResult {
  imported: number
  updated: number
  errors: number
}

export interface EgaRecord {
  id: string
  display: string
  sort_date: string | null
  record: Record<string, unknown>
}

export interface EgaTimelineEntry {
  id: string
  dto_type: string
  display: string
  sort_date: string | null
}

export const egaApi = {
  async importZip(file: File): Promise<EgaImportResult> {
    const form = new FormData()
    form.append("file", file)
    return api.postForm<EgaImportResult>("/ega/import", form)
  },

  getSummary: () => api.get<Record<string, number>>("/ega/summary"),

  getCosts: () =>
    api.get<{ ambulant_eur: number; medikamente_eur: number; medikamente_zuzahlung_eur: number }>("/ega/costs"),

  getRecords: (dtoType: string) =>
    api.get<{ dto_type: string; count: number; records: EgaRecord[] }>(`/ega/records/${dtoType}`),

  getTimeline: () =>
    api.get<{ count: number; entries: EgaTimelineEntry[] }>("/ega/timeline"),
}

// ─── FHIR Patientenakte ────────────────────────────────────────────────────

export interface FhirImportResult {
  imported: number
  updated: number
  errors: number
}

export interface FhirResource {
  resource: Record<string, unknown>
  imported_at: string
}

export interface FhirResourcesResponse {
  resource_type: string
  count: number
  resources: FhirResource[]
}

export interface FhirSummary {
  [resourceType: string]: number
}

export interface FhirTimelineEntry {
  resource_type: string
  label: string
  resource: Record<string, unknown>
  imported_at: string
}

export const fhirApi = {
  async importBundle(file: File): Promise<FhirImportResult> {
    const text = await file.text()
    const bundle = JSON.parse(text)
    return api.post<FhirImportResult>("/fhir/import", bundle)
  },

  async importEgaZip(file: File): Promise<FhirImportResult> {
    const form = new FormData()
    form.append("file", file)
    return api.postForm<FhirImportResult>("/fhir/import-ega", form)
  },

  getResources: (resourceType: string) =>
    api.get<FhirResourcesResponse>(`/fhir/resources/${resourceType}`),

  getSummary: () =>
    api.get<FhirSummary>("/fhir/summary"),

  getTimeline: () =>
    api.get<{ count: number; entries: FhirTimelineEntry[] }>("/fhir/timeline"),
}

// ─── Forschungs-APIs (Admin) ──────────────────────────────────────────────

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
