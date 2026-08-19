import { moduleMediaSources, moduleMediaWorkflows } from "@/modules/index.generated"
import type { ComponentType } from "react"

/** Ein Eintrag der Medien-Bibliothek, normalisiert über alle Quellen.
 *
 *  Der Core kennt nur diese Form — nicht die Rohtypen einzelner Module. */
export interface MediaLibraryItem {
  key: string
  kind: "video" | "image" | "audio"
  label: string
  /** Pfad relativ zum Projekt-Workspace, für Asset-Referenzen. */
  relPath: string
  /** Absoluter Pfad für Thumbnails/Preview via /api/files. */
  absPath: string | null
  /** Bekannte Dauer in Sekunden, sonst null. */
  duration: number | null
}

/** Eine Modul-Quelle, die Medien in den Videoschnitt einspeist.
 *
 *  Module exportieren `mediaSources` aus ihrer index.tsx; gen-modules sammelt
 *  sie ein. Fehlt das Modul, ist die Liste leer — der Core baut und läuft
 *  trotzdem. */
export interface MediaSource {
  id: string
  /** Wurzelverzeichnis des Projekts für absolute Pfade. Fehler → null. */
  resolveRoot: (projectId: string) => Promise<string | null>
  /** Bibliothekseinträge dieser Quelle. Fehler → leere Liste. */
  loadItems: (projectId: string, root: string | null) => Promise<MediaLibraryItem[]>
}

/** Ein Modul-Arbeitsbereich, der sich ins Media-Cockpit einklinkt (z. B. Atelier). */
export interface MediaWorkflow {
  id: string
  /** Schritte der linken Navigation. */
  steps: { id: string; title: string; text: string; icon?: string }[]
  component: ComponentType<{
    projectId?: string
    step?: string
    onStepChange?: (step: string) => void
    hideHeader?: boolean
  }>
}

export const mediaSources = moduleMediaSources as MediaSource[]
export const mediaWorkflows = moduleMediaWorkflows as MediaWorkflow[]

/** Erster verfügbarer Workflow (aktuell: Atelier) oder null wenn keiner installiert. */
export function primaryMediaWorkflow(): MediaWorkflow | null {
  return mediaWorkflows[0] ?? null
}

/** Projekt-Root über die erste Quelle, die einen liefert. */
export async function resolveMediaRoot(projectId: string): Promise<string | null> {
  for (const source of mediaSources) {
    try {
      const root = await source.resolveRoot(projectId)
      if (root) return root
    } catch {
      /* Quelle nicht verfügbar — nächste probieren. */
    }
  }
  return null
}

/** Sammelt die Bibliothek aller registrierten Quellen. Eine defekte Quelle
 *  darf die übrigen nicht verhindern. */
export async function loadMediaLibrary(projectId: string, root: string | null): Promise<MediaLibraryItem[]> {
  const results = await Promise.allSettled(mediaSources.map((source) => source.loadItems(projectId, root)))
  return results.flatMap((result) => (result.status === "fulfilled" ? result.value : []))
}
