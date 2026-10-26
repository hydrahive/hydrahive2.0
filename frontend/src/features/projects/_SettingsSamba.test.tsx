import i18next from "i18next"
import { renderToStaticMarkup } from "react-dom/server"
import { I18nextProvider, initReactI18next } from "react-i18next"
import { beforeAll, describe, expect, it } from "vitest"
import de from "@/i18n/locales/de/projects.json"
import { SambaSection } from "./_SettingsSamba"

const inst = i18next.createInstance()
beforeAll(async () => {
  await inst.use(initReactI18next).init({ lng: "de", ns: ["projects"], defaultNS: "projects",
    resources: { de: { projects: de } }, interpolation: { escapeValue: false } })
})
const html = (platform?: "linux" | "mac") => renderToStaticMarkup(
  <I18nextProvider i18n={inst}>
    <SambaSection samba={{ enabled: true, share_name: "P", user: "hhshare", password: "x", platform }} busy={false}
      error={null} onToggle={() => undefined} host="hydra.local" />
  </I18nextProvider>)

describe("Freigabe-Abschnitt im Projekt", () => {
  it("Mac: Titel, smb://-Adresse zuerst, Finder-Hinweis", () => {
    const h = html("mac")
    expect(h).toContain("Projekt im Netz freigeben")
    expect(h.indexOf("smb://")).toBeLessThan(h.indexOf("\\\\"))
    expect(h).toContain("Gehe zu → Mit Server verbinden")
  })
  it("Mac: am Mac selbst über den Benutzerordner (Finder verbindet sich nicht mit dem eigenen Mac)", () => {
    const h = html("mac")
    expect(h).toContain("Benutzerordner")
    expect(h).toContain("HydraHive")
    expect(h.indexOf("Benutzerordner")).toBeLessThan(h.indexOf("smb://"))
  })
  it("Linux: kein Benutzerordner-Hinweis", () => {
    expect(html("linux")).not.toContain("Benutzerordner")
  })
  it("Linux: wie bisher (SMB-Share, Windows-Adresse zuerst), Mac-Adresse als Zusatz", () => {
    const h = html("linux")
    expect(h).toContain("SMB-Share")
    expect(h.indexOf("\\\\")).toBeLessThan(h.indexOf("smb://"))
  })
})
