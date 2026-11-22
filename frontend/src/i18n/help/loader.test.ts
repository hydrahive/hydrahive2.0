import { describe, expect, it } from "vitest"
import { buildIndex } from "./loader"

const raw = (text: string) => () => Promise.resolve(text)

describe("Hilfe aus Kern und Modulen", () => {
  const core = {
    "./de/atelier.md": raw("# Atelier (Kern)"),
    "./de/buddy.md": raw("# Buddy"),
    "./en/buddy.md": raw("# Buddy EN"),
  }
  const modules = {
    "../../modules/atelier/help/de/atelier.md": raw("# Atelier (Modul)"),
    "../../modules/haushaltsbuch/help/de/haushaltsbuch.md": raw("# Haushaltsbuch"),
    "../../modules/evil/help/de/../../x.md": raw("böse"),
    "../../modules/x/help/deu/x.md": raw("falsche Sprache"),
  }

  it("findet Kern- und Modul-Artikel", () => {
    const { index } = buildIndex(core, modules)
    expect([...index.keys()].sort()).toEqual(["atelier", "buddy", "haushaltsbuch"])
  })

  it("das Modul gewinnt, wenn es dasselbe Thema mitbringt", async () => {
    const { index, origin } = buildIndex(core, modules)
    expect(await index.get("atelier")!.get("de")!()).toBe("# Atelier (Modul)")
    expect(origin.get("atelier")).toEqual({ source: "module", module: "atelier" })
    expect(origin.get("buddy")).toEqual({ source: "core", module: undefined })
  })

  it("ignoriert Pfade, die nicht dem Schema entsprechen", () => {
    const { index } = buildIndex(core, modules)
    expect(index.has("x")).toBe(false)
  })
})

describe("Modul-Hilfe liegt im Modul", () => {
  // Gegenprobe zum Umzug: Liegen alte Kopien wieder im Kern, wäre unklar, welcher Text gilt.
  const moved = ["archiver", "atelier", "blueprint", "boardgames", "cryptoboard", "deepresearch", "homeassistant",
    "mailbox", "minigames", "musicplayer", "notizbuch", "patientenakte", "scratchpad", "tasks", "videoeditor"]
  const coreFiles = Object.keys(import.meta.glob("./*/*.md"))

  it.each(moved)("kein Kern-Artikel mehr für %s", (topic) => {
    expect(coreFiles.filter((p) => p.endsWith(`/${topic}.md`))).toEqual([])
  })
})
