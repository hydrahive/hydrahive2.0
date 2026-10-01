/** Migriert beim Laden veraltete Parameternamen, damit sie beim nächsten
 *  Speichern im aktuellen Backend-Format persistiert werden.
 *  Eigene Datei ohne App-Abhängigkeiten: adapter.ts zieht über api-client die
 *  ganze App-Konfiguration nach, das scheitert im Testlauf ohne Build
 *  (generierte Dateien fehlen in der CI). */
export function migrateParams(subtype: string, params: Record<string, unknown>): Record<string, unknown> {
  if (subtype === "http_post" && params.body === undefined && typeof params.body_template === "string") {
    const { body_template, ...rest } = params
    return { ...rest, body: body_template }
  }
  if (subtype === "heartbeat_fired" && typeof params.task_id === "string") {
    const { task_id, ...rest } = params
    return { ...rest, schedule_id: params.schedule_id ?? task_id }
  }
  return params
}
