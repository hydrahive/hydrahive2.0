import { api } from "@/shared/api-client"

// ─── TK eGA (nativ) ─────────────────────────────────────────────────────────
// Read-only Import-Store, getrennt von der relationalen Akte. Pfade /ega/* + /fhir/*.

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

// ─── FHIR ────────────────────────────────────────────────────────────────────

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
}

// ─── Patientenakte (Single-User) ──────────────────────────────────────────
// Pfade behalten /health/patientenakte (= Backend-Router-Prefix /api/health/patientenakte).

export type AkteEntityKey =
  | 'conditions' | 'medications' | 'observations'
  | 'events' | 'imaging' | 'allergies'
  | 'practitioners' | 'documents' | 'notes'

export interface AkteUiField {
  key: string
  label: string
  type: 'text' | 'number' | 'date' | 'textarea' | 'select'
  required: boolean
  options: string[]
  placeholder: string | null
}

export interface AkteEntitySchema {
  key: string
  label: string
  label_fields: string[]
  list_columns: string[]
  date_field: string | null
  numeric_fields: string[]
  ui_fields: AkteUiField[]
}

export interface AkteSchemaResponse {
  entities: Record<AkteEntityKey, AkteEntitySchema>
}

export interface AktePatient {
  id: string
  slug: string
  name: string
  vorname: string
  geburtsdatum: string
  geschlecht: string
  versicherung?: Record<string, unknown>
  counts?: Record<string, number>
}

export interface AkteRecord {
  id: string
  external_id?: string
  label: string
  sort_date: string
  verifiziert: number
  record: Record<string, unknown>
  // Index-Signatur: erfüllt die ResourceTable<T extends Record<string, unknown>>-Constraint
  [key: string]: unknown
}

export interface AkteTimelineEntry {
  entity: AkteEntityKey
  label: string
  sort_date: string
  record: Record<string, unknown>
  verifiziert: number
}

// Das Backend liefert Entitäts-Records FLACH ({id, diagnose, icd_code, sort_date, …}).
// Die UI erwartet {id, label, sort_date, verifiziert, record:{…}}. Dieser Adapter
// übersetzt die flache Antwort und leitet ein sinnvolles Label je Entität ab.
// label_fields kommen aus dem Schema-Endpoint (SSOT).
function toAkteRecord(row: Record<string, unknown>, labelFields: string[]): AkteRecord {
  const labelField = labelFields.find((f) => row[f])
  const label = labelField ? String(row[labelField]) : '—'
  return {
    id: String(row.id ?? ''),
    external_id: row.external_id ? String(row.external_id) : undefined,
    label,
    sort_date: (row.sort_date as string) ?? '',
    verifiziert: Number(row.verifiziert ?? 0),
    record: row,
  }
}

export const akteApi = {
  getSchema: () => api.get<AkteSchemaResponse>('/health/patientenakte/_schema'),

  // Own Akte
  getOwn: () => api.get<AktePatient>('/health/patientenakte'),

  createOwn: (data: Partial<AktePatient>) =>
    api.post<{ id: string }>('/health/patientenakte', data),

  updateOwn: (data: Partial<AktePatient>) =>
    api.patch<{ ok: boolean }>('/health/patientenakte', data),

  getSummary: () =>
    api.get<Record<string, number>>('/health/patientenakte/summary'),

  getTimeline: async (): Promise<AkteTimelineEntry[]> => {
    const rows = await api.get<AkteTimelineEntry[]>('/health/patientenakte/timeline')
    // Backend liefert verifiziert flach im record; UI liest es oben → nachziehen.
    return rows.map((e) => ({
      ...e,
      verifiziert: Number(e.verifiziert ?? (e.record as Record<string, unknown>)?.verifiziert ?? 0),
    }))
  },

  // Entities
  listEntity: async (entity: AkteEntityKey, params?: { q?: string; status?: string }, labelFields?: string[]): Promise<AkteRecord[]> => {
    const sp = new URLSearchParams()
    if (params?.q) sp.set('q', params.q)
    if (params?.status) sp.set('status', params.status)
    const qs = sp.toString()
    const rows = await api.get<Record<string, unknown>[]>(
      `/health/patientenakte/${entity}${qs ? '?' + qs : ''}`
    )
    const lf = labelFields ?? ['id']
    return rows.map((row) => toAkteRecord(row, lf))
  },

  createEntity: (entity: AkteEntityKey, data: Record<string, unknown>) =>
    api.post<{ id: string }>(`/health/patientenakte/${entity}`, data),

  updateEntity: (entity: AkteEntityKey, eid: string, data: Record<string, unknown>) =>
    api.patch<{ ok: boolean }>(`/health/patientenakte/${entity}/${eid}`, data),

  deleteEntity: (entity: AkteEntityKey, eid: string) =>
    api.delete<{ ok: boolean }>(`/health/patientenakte/${entity}/${eid}`),

  verifyEntity: (entity: AkteEntityKey, eid: string) =>
    api.patch<{ ok: boolean }>(`/health/patientenakte/${entity}/${eid}`, { verifiziert: 1 }),
}
