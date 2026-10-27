export type MascotState =
  | "idle"
  | "working"
  | "speaking"
  | "sleeping"
  | "confused"
  | "celebrate"
  | "thinking"
  | "error"

/** Tills bunte Hydra in acht Stimmungen (public/hydra/, Task 0dda5420). Entstanden mit seiner
 *  Vollbild-Hydra als Vorlage, lokal freigestellt; Quelle: generated/hydra-design/zustaende/. */
export const MASCOT_SRC: Record<MascotState, string> = {
  idle: "/hydra/idle.webp",
  working: "/hydra/working.webp",
  speaking: "/hydra/speaking.webp",
  sleeping: "/hydra/sleeping.webp",
  confused: "/hydra/confused.webp",
  celebrate: "/hydra/celebrate.webp",
  thinking: "/hydra/thinking.webp",
  error: "/hydra/error.webp",
}
