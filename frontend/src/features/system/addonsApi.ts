import { api } from "@/shared/api-client"

/** Zusatz-Module, die im Admin-Cockpit nachinstalliert werden können (docs/specs/installer-core-first.md §3). */
export type AddonId = "containers" | "vms" | "samba" | "whatsapp" | "voice" | "tailscale"

export interface AddonItem {
  id: AddonId
  installed: boolean
  enabled: boolean
  restarts_service: boolean
  requires: AddonId[]
  hint: "wsl" | null
}

export interface AddonsResponse {
  items: AddonItem[]
  /** Name des laufenden Auftrags, „?“ bei unlesbarer Anfrage, sonst null. */
  running: string | null
}

export const addonsApi = {
  list: () => api.get<AddonsResponse>("/system/addons"),
  install: (id: AddonId) => api.post<{ started: boolean }>(`/system/addons/${id}/install`, {}),
  log: (tail = 300) => api.get<{ lines: string[]; exists: boolean }>(`/system/addons/log?tail=${tail}`),
}

/** Ergebnis des LETZTEN Laufs im Log (installer/addon-ctl.sh). Ältere Läufe davor zählen nicht. */
export function addonOutcome(lines: string[], id: string): "ok" | "failed" | null {
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i]
    if (line.includes("[hh2-addon] FERTIG: install ")) return line.includes(`FERTIG: install ${id} ok`) ? "ok" : null
    if (line.includes("[hh2-addon] FEHLER:")) return "failed"
    if (line.includes("[hh2-addon] ===== ")) return null
  }
  return null
}

/** Nur die Zeilen des letzten Laufs (ab der letzten Kopfzeile) – das Log enthält auch alte Läufe. */
export function lastRun(lines: string[]): string[] {
  for (let i = lines.length - 1; i >= 0; i--) {
    if (lines[i].includes("[hh2-addon] ===== ")) return lines.slice(i)
  }
  return lines
}
