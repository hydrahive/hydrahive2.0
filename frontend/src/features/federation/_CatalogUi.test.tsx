// Föderations-Katalog Etappe 1 (docs/specs/federation-catalog.md §Oberfläche): Schalter je Server,
// Abschnitt „Katalog-Sync“ und Texte de/en.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
import { PeerCatalogToggles } from "./_PeerCatalogToggles"
import { CatalogSyncForm } from "./_CatalogSyncForm"
import { toDraft } from "./_catalogSync"
import type { CatalogSettings, Peer } from "./types"
import deFed from "@/i18n/locales/de/federation.json"
import enFed from "@/i18n/locales/en/federation.json"
import deErr from "@/i18n/locales/de/errors.json"
import enErr from "@/i18n/locales/en/errors.json"

const peer = (over: Partial<Peer> = {}): Peer => ({
  id: "p1", name: "hydrahive-vps", url: "https://100.1.2.3", fingerprint: "abcd", status: "active",
  created_at: "", confirmed_at: null, last_seen: null, allowed_agents: [],
  is_hub: false, catalog_accept: false, ...over,
} as Peer)

const settings = (over: Partial<CatalogSettings> = {}): CatalogSettings => ({
  enabled: false, interval_seconds: 300, users: [], excluded_projects: [],
  hub: null, accepting_from: [],
  last_push_at: null, last_ok_at: null, last_full_at: null, last_error: null, ...over,
})

const switches = (h: string) =>
  [...h.matchAll(/<button[^>]*role="switch"[^>]*>/g)].map(m => ({
    label: /aria-label="([^"]+)"/.exec(m[0])?.[1],
    checked: /aria-checked="true"/.test(m[0]),
    disabled: /disabled=""/.test(m[0]),
  }))

describe("Reiter „Server“: Schalter je Partner", () => {
  const render = (p: Peer) =>
    renderToStaticMarkup(<PeerCatalogToggles peer={p} onSetHub={() => {}} onSetAccept={() => {}} />)

  it("aktiver Partner: beide Schalter bedienbar, aus", () => {
    expect(switches(render(peer()))).toEqual([
      { label: "catalog.hub_toggle", checked: false, disabled: false },
      { label: "catalog.accept_toggle", checked: false, disabled: false },
    ])
  })
  it("Hub-Markierung wird angezeigt", () => {
    expect(switches(render(peer({ is_hub: true })))[0].checked).toBe(true)
  })
  it("nicht aktiver Partner: Einschalten gesperrt, mit Hinweis", () => {
    const h = render(peer({ status: "pending" }))
    expect(switches(h).map(s => s.disabled)).toEqual([true, true])
    expect(h).toContain("catalog.only_active")
  })
  it("gesperrter Partner, der noch Hub ist: Ausschalten bleibt möglich", () => {
    const s = switches(render(peer({ status: "blocked", is_hub: true })))
    expect(s[0]).toEqual({ label: "catalog.hub_toggle", checked: true, disabled: false })
    expect(s[1].disabled).toBe(true)
  })
})

describe("Abschnitt „Katalog-Sync“", () => {
  const render = (s: CatalogSettings, draft = toDraft(s), extra: { users?: string[] } = {}) =>
    renderToStaticMarkup(
      <CatalogSyncForm settings={s} draft={draft} users={extra.users ?? ["anna", "till"]}
        projects={[{ id: "p1", name: "Geheim" }]} saving={false} saved={false} error=""
        onChange={() => {}} onSave={() => {}} onReset={() => {}} />,
    )

  it("Standard: Sync aus, kein Hub, kein Nutzer gewählt, Speichern gesperrt", () => {
    const h = render(settings())
    expect(switches(h)).toEqual([{ label: "catalog.sync_toggle", checked: false, disabled: false }])
    expect(h).toContain("catalog.hub_none")
    expect(h).toContain("catalog.users_none_selected")
    expect(h).not.toContain('aria-pressed="true"')
    expect(h).toMatch(/<button[^>]*disabled=""[^>]*>catalog.save<\/button>/)
    expect(h).toContain("catalog.never")
  })
  it("zeigt Hub, Partner mit Annahme, gewählte Nutzer und ausgeschlossene Projekte", () => {
    const h = render(settings({
      enabled: true, users: ["till"], excluded_projects: ["p1"],
      hub: { id: "p1", name: "hydrahive-vps", status: "active" },
      accepting_from: [{ id: "p2", name: "hydrahome" }],
    }))
    expect(switches(h)[0].checked).toBe(true)
    expect(h).toContain("hydrahive-vps")
    expect(h).toContain("hydrahome")
    expect(h).toMatch(/aria-pressed="true"[^>]*>till</)
    expect(h).toMatch(/aria-pressed="false"[^>]*>anna</)
    expect(h).toMatch(/aria-pressed="true"[^>]*>Geheim</)
  })
  it("Hub mit nicht aktiver Kopplung wird markiert", () => {
    expect(render(settings({ hub: { id: "p1", name: "vps", status: "blocked" } }))).toContain("catalog.hub_inactive")
  })
  it("ungültiges Intervall: Hinweis und Speichern gesperrt", () => {
    const s = settings()
    const h = render(s, { ...toDraft(s), interval: "30" })
    expect(h).toContain("catalog.interval_invalid")
    expect(h).toContain('aria-invalid="true"')
    expect(h).toMatch(/<button[^>]*disabled=""[^>]*>catalog.save<\/button>/)
  })
  it("gültige Änderung: Speichern frei, Verwerfen sichtbar", () => {
    const s = settings()
    const h = render(s, { ...toDraft(s), interval: "600" })
    expect(h).not.toMatch(/<button[^>]*disabled=""[^>]*>catalog.save<\/button>/)
    expect(h).toContain("catalog.reset")
  })
  it("letzter Fehler wird im Status angezeigt", () => {
    expect(render(settings({ last_error: "Hub nimmt noch nicht an" }))).toContain("Hub nimmt noch nicht an")
  })
  it("bekannte Fehlercodes werden übersetzt, unbekannte bleiben roh (AK 2: Grund sichtbar)", () => {
    const h = render(settings({ last_error: "peer_catalog_not_accepted" }))
    expect(h).toContain("catalog.reason.peer_catalog_not_accepted")
    const mixed = render(settings({ last_error: "source_failed:idea, etwas_neues" }))
    expect(mixed).toContain("catalog.reason.source_failed")
    expect(mixed).toContain("etwas_neues")
  })
})

describe("Knopf „Jetzt abgleichen“", () => {
  const render = (over: Record<string, unknown> = {}, draft?: ReturnType<typeof toDraft>) => {
    const s = settings({ enabled: true, users: ["till"], last_full_at: "2026-11-21T10:00:00.000+00:00" })
    return renderToStaticMarkup(
      <CatalogSyncForm settings={s} draft={draft ?? toDraft(s)} users={["till"]} projects={[]}
        saving={false} saved={false} error="" onChange={() => {}} onSave={() => {}} onReset={() => {}}
        onSyncNow={() => {}} {...over} />,
    )
  }
  it("sichtbar und bedienbar, zeigt letzten vollständigen Abgleich", () => {
    const h = render()
    expect(h).toMatch(/<button[^>]*>catalog.sync_now<\/button>/)
    expect(h).not.toMatch(/<button[^>]*disabled=""[^>]*>catalog.sync_now<\/button>/)
    expect(h).toContain("catalog.last_full")
  })
  it("gesperrt, solange abgeglichen wird oder ungespeicherte Änderungen da sind", () => {
    expect(render({ syncing: true })).toMatch(/<button[^>]*disabled=""[^>]*>catalog.syncing<\/button>/)
    const s = settings({ enabled: true, users: ["till"] })
    expect(render({}, { ...toDraft(s), interval: "900" })).toContain("catalog.sync_now_hint")
  })
  it("zeigt Ergebnis ok bzw. inactive", () => {
    expect(render({ syncResult: "ok" })).toContain("catalog.sync_now_ok")
    expect(render({ syncResult: "inactive" })).toContain("catalog.sync_now_inactive")
  })
})

describe("Texte de/en", () => {
  it("gleiche Schlüssel im Abschnitt catalog", () => {
    expect(Object.keys(enFed.catalog).sort()).toEqual(Object.keys(deFed.catalog).sort())
  })
  it("alle im Code genutzten catalog-Schlüssel existieren", () => {
    const used = ["peer_title", "hub_toggle", "hub_hint", "accept_toggle", "accept_hint", "only_active", "sync_title",
      "sync_subtitle", "sync_toggle", "sync_hint", "hub_label", "hub_none", "hub_inactive", "accepting_label",
      "interval_label", "interval_hint", "interval_invalid", "users_label", "users_empty", "users_none_selected",
      "projects_label", "projects_empty", "status_label", "last_ok", "last_push", "last_error", "never", "save",
      "saving", "saved", "reset", "load_error", "switch_hub_confirm", "last_full", "sync_now", "syncing",
      "sync_now_ok", "sync_now_inactive", "sync_now_hint"]
    for (const k of used) {
      expect(deFed.catalog).toHaveProperty(k)
      expect(enFed.catalog).toHaveProperty(k)
    }
  })
  it("alle Fehlercodes des Sync-Status haben Texte de/en", async () => {
    const { REASON_CODES } = await import("./_catalogSync")
    for (const code of REASON_CODES) {
      expect(deFed.catalog.reason).toHaveProperty(code)
      expect(enFed.catalog.reason).toHaveProperty(code)
    }
  })
  it("409/400-Codes des Backends sind übersetzt (sonst sähe man den rohen Code)", () => {
    for (const code of ["peer_not_active", "catalog_hub_exists", "catalog_hub_conflict", "catalog_user_unknown"]) {
      expect(deErr).toHaveProperty(code)
      expect(enErr).toHaveProperty(code)
    }
    expect(deErr.catalog_hub_exists).toContain("{{name}}")
    expect(deErr.catalog_user_unknown).toContain("{{username}}")
  })
})
