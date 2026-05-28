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

  getResources: (resourceType: string) =>
    api.get<FhirResourcesResponse>(`/fhir/resources/${resourceType}`),

  getSummary: () =>
    api.get<FhirSummary>("/fhir/summary"),

  getTimeline: () =>
    api.get<{ count: number; entries: FhirTimelineEntry[] }>("/fhir/timeline"),
}
