import { api } from "@/shared/api-client"

export interface Briefing {
  generated_at: string
  date: string
  open_items: string
  went_well: string
  went_badly: string
  today: string
  error: string | null
}

export interface ZahnfeeConfig {
  enabled: boolean
  model: string
  run_hour: number
  lookback_hours: number
  source_datamining: boolean
  source_mail: boolean
  soul: string
}

export const zahnfeeApi = {
  briefing: () => api.get<{ briefing: Briefing | null }>("/zahnfee/briefing"),
  config: () => api.get<ZahnfeeConfig>("/zahnfee/config"),
  updateConfig: (body: Partial<ZahnfeeConfig>) => api.put<ZahnfeeConfig>("/zahnfee/config", body),
  run: () => api.post<{ ok: boolean; briefing: Briefing }>("/zahnfee/run", {}),
}
