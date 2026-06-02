import { api } from "@/shared/api-client"

export type SettingType = "string" | "bool" | "int" | "secret"

export interface EditableSetting {
  key: string
  group: string
  label: string
  type: SettingType
  help: string
  value: string
  is_set: boolean
  overridden: boolean
}

export const settingsApi = {
  list: () => api.get<{ settings: EditableSetting[] }>("/system/settings"),
  update: (key: string, value: string) =>
    api.put<EditableSetting>(`/system/settings/${encodeURIComponent(key)}`, { value }),
}
