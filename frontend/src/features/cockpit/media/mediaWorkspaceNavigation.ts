export type MediaWorkspaceArea = "idea" | "prompts" | "screenplay" | "characters" | "style" | "assets" | "timeline"

export const mediaWorkspaceAreas: Array<{ id: MediaWorkspaceArea; title: string; text: string; step: number }> = [
  { id: "idea", title: "Idee", text: "Grundidee, Ziel und Format", step: 0 },
  { id: "prompts", title: "Prompts", text: "Entwürfe und Promptarchiv", step: 0 },
  { id: "screenplay", title: "Drehbuch & Regie", text: "Akte, Szenen und Shots", step: 1 },
  { id: "characters", title: "Charaktere", text: "Personen, Stimmen und Looks", step: 2 },
  { id: "style", title: "Stil / CI", text: "Bildsprache, Farben und Format", step: 2 },
  { id: "assets", title: "Assets", text: "Bilder, Video, Audio und Referenzen", step: 2 },
  { id: "timeline", title: "Schnitt", text: "Spuren, Clips und Export", step: 4 },
]
