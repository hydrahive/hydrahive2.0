// Plan docs/plans/admin-luecken-schliessen.md, Task 2: Warnung „Zugang ohne Host“ auch im Admin-Cockpit.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
import { CredentialCockpitCard, UnboundBanner } from "./CredentialCockpitCard"
import type { Credential } from "@/features/credentials/types"

const plain = (html: string) => html.replace(/&quot;/g, '"')
const cred = (p: Partial<Credential> = {}): Credential => ({
  name: "gitea", type: "bearer", value: "", value_set: true, url_pattern: "https://git.example/*",
  host_bound: true, description: "", header_name: "", query_param: "", ...p,
})
const noop = () => {}

describe("Zugangsdaten im Admin-Cockpit", () => {
  it("Banner ohne ungebundene Zugänge: nichts", () => {
    expect(renderToStaticMarkup(<UnboundBanner count={0} />)).toBe("")
  })
  it("Banner nennt die Anzahl", () => {
    expect(plain(renderToStaticMarkup(<UnboundBanner count={2} />))).toContain('unbound_banner:{"count":2}')
  })
  it("Karte eines Zugangs ohne Host zeigt den Hinweis", () => {
    expect(renderToStaticMarkup(<CredentialCockpitCard credential={cred({ host_bound: false })} onOpen={noop} />)).toContain("not_host_bound")
  })
  it("Karte eines gebundenen Zugangs zeigt keinen Hinweis", () => {
    const html = renderToStaticMarkup(<CredentialCockpitCard credential={cred()} onOpen={noop} />)
    expect(html).not.toContain("not_host_bound")
    expect(html).toContain("gitea")
  })
  it("alter Eintrag ohne Feld zeigt keinen Hinweis", () => {
    expect(renderToStaticMarkup(<CredentialCockpitCard credential={cred({ host_bound: undefined })} onOpen={noop} />)).not.toContain("not_host_bound")
  })
})
