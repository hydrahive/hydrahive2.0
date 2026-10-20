// Admin-Konsole → Media-Backends: was ein eingelesener ComfyUI-Workflow speichert (Nachtrag 19.10.2026).

/** Platzhalter ohne leere Einträge; Vorlagen-Verbindungen nur für gesetzte Vorlagen (sonst bliebe ein Eingang hängen). */
export function workflowMaps(mapping: Record<string, string>, links: Record<string, string>) {
  const placeholders = Object.fromEntries(Object.entries(mapping).filter(([, v]) => v))
  const reference_links = Object.fromEntries(Object.entries(links).filter(([k, v]) => v && placeholders[k]))
  return Object.keys(reference_links).length ? { placeholders, reference_links } : { placeholders }
}
