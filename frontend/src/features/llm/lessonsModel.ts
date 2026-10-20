// Modell für „Lehren mit Beleg“ (docs/specs/lehren-mit-beleg.md 10a): "" = wie Chat, "off" = keine Lehren.
export const LESSONS_OFF = "off"

export function lessonsChoice(cfg: { lessons_model?: string }): string {
  return cfg.lessons_model ?? ""
}

export function lessonsValue<T extends { lessons_model?: string }>(cfg: T, choice: string): T {
  return { ...cfg, lessons_model: choice }
}
