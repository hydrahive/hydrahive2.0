// Standard-Modelle speichern (Schutz vom 20.10.2026): jede Auswahl einzeln über PUT /llm/default/{zweck}, damit eine
// Änderung nie die ganze Datei – Anbieter, Schlüssel, lokale Backends – mit einem noch leeren Platzhalter überschreibt.
// Nur das Embedding-Modell braucht das vollständige Speichern (der Server prüft dabei die Vektor-Dimension).
export type SavePurpose = "chat" | "image" | "music" | "tts" | "stt" | "video" | "lessons"

const SINGLE: ReadonlySet<string> = new Set(["chat", "image", "music", "tts", "stt", "video", "lessons"])

export function purposeFor(purpose: string): SavePurpose | null {
  return SINGLE.has(purpose) ? (purpose as SavePurpose) : null
}

/** Ob die echten Einstellungen vom Server da sind (null = noch nicht geladen). */
export function configLoaded<T>(config: T | null): config is T {
  return config !== null
}
