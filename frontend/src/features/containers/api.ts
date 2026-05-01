import { api } from "@/shared/api-client"
import type { Container, ContainerCreateInput, ContainerInfo } from "./types"

export const containersApi = {
  list: () => api.get<Container[]>("/containers"),
  get: (id: string) => api.get<Container>(`/containers/${id}`),
  info: (id: string) => api.get<ContainerInfo>(`/containers/${id}/info`),
  create: (input: ContainerCreateInput) => api.post<Container>("/containers", input),
  update: (id: string, patch: {
    name?: string
    description?: string | null
    cpu?: number | null
    ram_mb?: number | null
    clear_cpu?: boolean
    clear_ram?: boolean
  }) => api.patch<Container>(`/containers/${id}`, patch),
  remove: (id: string) => api.delete<void>(`/containers/${id}`),
  start: (id: string) => api.post<Container>(`/containers/${id}/start`, {}),
  stop: (id: string) => api.post<Container>(`/containers/${id}/stop`, {}),
  restart: (id: string) => api.post<Container>(`/containers/${id}/restart`, {}),
  quickImages: () => api.get<string[]>("/containers/quick-images"),
  log: (id: string) => api.get<{ text: string }>(`/containers/${id}/log`),
  config: (id: string) => api.get<{ text: string }>(`/containers/${id}/config`),
}
