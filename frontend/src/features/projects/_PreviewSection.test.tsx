import i18next from "i18next"
import { renderToStaticMarkup } from "react-dom/server"
import { I18nextProvider, initReactI18next } from "react-i18next"
import { beforeAll, describe, expect, it } from "vitest"
import de from "@/i18n/locales/de/projects.json"
import en from "@/i18n/locales/en/projects.json"
import { PreviewSectionView } from "./_PreviewSection"

const inst = i18next.createInstance()
beforeAll(async () => {
  await inst.use(initReactI18next).init({ lng: "de", ns: ["projects"], defaultNS: "projects",
    resources: { de: { projects: de } }, interpolation: { escapeValue: false } })
})

const noop = () => undefined
function html(status: { port: number; running: boolean } | null, containerMode = false, error: string | null = null) {
  return renderToStaticMarkup(<I18nextProvider i18n={inst}>
    <PreviewSectionView status={status} containerMode={containerMode} loading={false} opening={false} error={error}
      onRecheck={noop} onOpen={noop} />
  </I18nextProvider>)
}
const hasOpenButton = (h: string) => h.includes('data-action="open"')

describe("Abschnitt „Testseite“", () => {
  it("läuft: Status, Port und Knopf „Testseite öffnen“", () => {
    const h = html({ port: 18100, running: true })
    expect(h).toContain("Testseite läuft")
    expect(h).toContain("Port der Testseite: 18100")
    expect(hasOpenButton(h)).toBe(true)
    expect(h).toContain("Testseite öffnen")
    expect(h).not.toContain("Noch keine Testseite gestartet")
  })

  it("läuft nicht: Hinweis und Port, KEIN Knopf", () => {
    const h = html({ port: 18101, running: false })
    expect(h).toContain("Noch keine Testseite gestartet")
    expect(h).toContain("Port der Testseite: 18101")
    expect(hasOpenButton(h)).toBe(false)
  })

  it("Hinweise: zuletzt geöffnete Testseite gilt, Zertifikat, „Neu prüfen“", () => {
    const h = html({ port: 18100, running: true })
    expect(h).toContain("Pro Browser ist immer die zuletzt geöffnete Testseite aktiv.")
    expect(h).toContain("Beim ersten Öffnen fragt der Browser nach dem Zertifikat")
    expect(h).toContain('data-action="recheck"')
  })

  it("Status noch nicht geladen oder Fehler: kein Knopf, Fehler sichtbar", () => {
    const h = html(null, false, "Kein Zugriff auf dieses Projekt")
    expect(hasOpenButton(h)).toBe(false)
    expect(h).toContain("Kein Zugriff auf dieses Projekt")
  })

  it("Container-Projekt: kein Knopf, kein „Neu prüfen“, Hinweis", () => {
    const h = html({ port: 18100, running: true }, true)
    expect(h).toContain("im Container")
    expect(hasOpenButton(h)).toBe(false)
    expect(h).not.toContain('data-action="recheck"')
  })

  it("Texte gibt es in Deutsch und Englisch mit denselben Schlüsseln", () => {
    expect(Object.keys(de.preview).sort()).toEqual(Object.keys(en.preview).sort())
  })
})
