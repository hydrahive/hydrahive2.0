// docs/specs/startdesktop.md (Punkt 6): Module zeigten in der Leiste rohe Schlüssel („aiSecurity“,
// „musicplayer“, „bg_title“), weil navLabel nur <key>:title kannte.
import { describe, expect, it } from "vitest"
import type { TFunction } from "i18next"
import { navLabel } from "./nav-label"

const DICT: Record<string, string> = {
  "items.projects": "Projekte",
  "storyteller:title": "Storyteller",
  "musicplayer:musicplayer": "Mediaplayer",
  "boardgames:bg_title": "Brettspiele",
}
// Nachbau von i18next-Verhalten: Schlüssel gefunden → Text, sonst defaultValue, sonst der Schlüssel selbst.
// Modul-Bündel, deren Text direkt auf oberster Ebene steht (ai-security: { aiSecurity: "AI-Sicherheit" }),
// kann i18next per t() nicht auflösen (geprüft 24.10.) – navLabel liest dann das Bündel selbst.
const BUNDLES: Record<string, unknown> = { aiSecurity: "AI-Sicherheit", vitrine: { vitrine: "Vitrine" } }
const bundle = (ns: string) => BUNDLES[ns]
const t = ((key: string, opts?: { defaultValue?: string }) => DICT[key] ?? opts?.defaultValue ?? key) as unknown as TFunction

describe("navLabel", () => {
  it("Kern-Einträge aus nav:items", () => {
    expect(navLabel(t, "projects")).toBe("Projekte")
  })
  it("Module mit <key>:title wie bisher", () => {
    expect(navLabel(t, "storyteller")).toBe("Storyteller")
  })
  it("Module mit Text direkt unter dem Schlüssel (oberste Ebene)", () => {
    expect(navLabel(t, "aiSecurity", "ai-security", bundle)).toBe("AI-Sicherheit")
  })
  it("Module mit Text im eigenen Namensraum unter demselben Schlüssel", () => {
    expect(navLabel(t, "musicplayer", "musicplayer")).toBe("Mediaplayer")
  })
  it("Module mit anderem Schlüssel im eigenen Namensraum", () => {
    expect(navLabel(t, "bg_title", "boardgames")).toBe("Brettspiele")
  })
  it("ohne Treffer bleibt der Schlüssel (Rückfall wie bisher)", () => {
    expect(navLabel(t, "gibtsnicht", "modul", bundle)).toBe("gibtsnicht")
  })
  it("ein Bündel, das kein Text ist, wird nicht als Name benutzt", () => {
    expect(navLabel(t, "vitrine", "vitrine", () => ({ vitrine: "x" }))).toBe("vitrine")
  })
  it("Kern- und title-Treffer gehen dem Bündel vor", () => {
    expect(navLabel(t, "projects", undefined, () => "FALSCH")).toBe("Projekte")
    expect(navLabel(t, "storyteller", "storyteller", () => "FALSCH")).toBe("Storyteller")
  })
})
