import { api } from "@/shared/api-client"
import type { HubIndex, InstallResponse, InstalledPlugin } from "./types"

export const pluginsApi = {
  hub: () => api.get<HubIndex>("/plugins/hub"),
  installed: () => api.get<InstalledPlugin[]>("/plugins/installed"),
  install: (name: string) => api.post<InstallResponse>("/plugins/install", { name }),
  uninstall: (name: string) => api.post<InstallResponse>("/plugins/uninstall", { name }),
  update: (name: string) => api.post<InstallResponse>("/plugins/update", { name }),
}
