// Fehlerbericht (docs/plans/help-error-report.md): Entwurf, Status, Senden, Verwerfen.
import { api } from "@/shared/api-client"

export interface ReportDraft { id: string; subject: string; body: string; to: string; mailto?: string; truncated?: boolean }
export interface ReportStatus { enabled: boolean; mail_account: boolean; can_setup: boolean }
export type ReportSendResult =
  | { sent: true; to: string }
  | { sent: false; reason: "no_mail_account"; to: string; mailto: string; truncated: boolean; subject: string; body: string }

const B = "/helpdesk/report"

export const reportApi = {
  status: () => api.get<ReportStatus>(`${B}-status`),
  get: (id: string) => api.get<ReportDraft>(`${B}/${encodeURIComponent(id)}`),
  send: (id: string) => api.post<ReportSendResult>(`${B}/${encodeURIComponent(id)}/send`, {}),
  discard: (id: string) => api.delete<void>(`${B}/${encodeURIComponent(id)}`),
}
