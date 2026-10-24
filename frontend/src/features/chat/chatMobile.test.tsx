// docs/specs/chat-mobile-compact.md (Task 37232294): Auf dem Handy brach der Chat-Kopf in mehrere
// Zeilen um, die Eingabe brauchte 152 px und Knöpfe wurden abgeschnitten.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k, i18n: { language: "de" } }) }))
vi.mock("./api", () => ({ chatApi: { tokens: vi.fn(() => new Promise(() => {})) } }))
vi.mock("@/i18n/HelpDrawer", () => ({ HelpDrawer: () => null }))
vi.mock("./EmotePicker", () => ({ EmotePicker: () => null }))
vi.mock("./PromptArchivePicker", () => ({ PromptArchivePicker: () => null }))
vi.mock("./useVoiceInput", () => ({ useVoiceInput: () => ({ state: "idle", toggle: () => {} }) }))
vi.mock("@/features/auth/useAuthStore", () => ({ useAuthStore: { getState: () => ({ token: "T" }) } }))
import { ChatHeader } from "./_ChatHeader"
import { MessageInput } from "./MessageInput"
import { HelpButton } from "@/i18n/HelpButton"
import type { Session } from "./types"

const session = { id: "01a16b93abcdef", title: "Testsitzung", agent_id: "a1", project_id: "p1" } as unknown as Session
const header = (cockpitMode: boolean, extra: Record<string, unknown> = {}) => renderToStaticMarkup(
  <ChatHeader session={session} agent={{ id: "a1", name: "A", type: "x", llm_model: "m/x", status: "active" }}
    orphaned={false} compacting={false} compactNote={null} lastTurnTokens={null} busy={false} systemPrompt=""
    onCompact={() => {}} onDelete={() => {}} onNewSession={() => {}} tokenRefresh={0} cockpitMode={cockpitMode}
    sessions={cockpitMode ? [session] : []} activeSessionId={session.id} onSelectSession={() => {}} {...extra} />,
)
/** Alle <button …>…</button> mit ihrem Inhalt. */
const buttons = (html: string) => [...html.matchAll(/<button([^>]*)>([\s\S]*?)<\/button>/g)].map((m) => ({ attrs: m[1], inner: m[2] }))
const classOf = (attrs: string) => (attrs.match(/class="([^"]*)"/)?.[1] ?? "").split(/\s+/)

describe.each([["Projekt-Cockpit", true], ["Werkstatt", false]])("ChatHeader (%s) auf dem Handy", (_name, cockpit) => {
  it("Komprimieren und Neuer Chat: Text nur ab sm, Knopf behält aria-label", () => {
    const html = header(cockpit as boolean)
    for (const label of [cockpit ? "Komprimieren" : "compact.button", cockpit ? "Neuer Chat" : "session.new_chat"]) {
      const b = buttons(html).find((x) => x.inner.includes(label))
      expect(b, label).toBeDefined()
      expect(b!.inner).toMatch(new RegExp(`<span class="hidden sm:inline">\\s*${label}\\s*</span>`))
      expect(b!.attrs).toMatch(/aria-label="[^"]+"/)
    }
  })

  it("Füllstand ist unter sm ausgeblendet", () => {
    const html = header(cockpit as boolean)
    expect(html).toMatch(/<div class="hidden sm:flex"[^>]*data-token-meter="1"/)
  })

  it("Sitzungsnummer ist unter sm ausgeblendet", () => {
    expect(header(cockpit as boolean)).toMatch(/<span class="hidden sm:inline">[^<]*01a16b93…<\/span>/)
  })
})

describe("ChatHeader Projekt-Cockpit: Modellzeile", () => {
  it("bricht auf dem Handy nicht um, langer Modellname wird gekürzt und steht voll im title", () => {
    const html = header(true, { agent: { id: "a1", name: "A", type: "x", llm_model: "openrouter/anthropic/claude-sonnet-4.5", status: "active" } })
    const line = html.match(/<p class="([^"]*)">/)
    expect(line).not.toBeNull()
    const cls = line![1].split(" ")
    expect(cls).toContain("flex-nowrap")
    expect(cls).toContain("sm:flex-wrap")
    expect(cls).not.toContain("flex-wrap")
    expect(html).toMatch(/<span class="[^"]*\btruncate\b[^"]*" title="openrouter\/anthropic\/claude-sonnet-4\.5">· openrouter\/anthropic\/claude-sonnet-4\.5<\/span>/)
  })
})

describe("ChatHeader Projekt-Cockpit: Sitzungsauswahl", () => {
  it("ist auf dem Handy schmal (höchstens 140 px), ab sm wie bisher", () => {
    const b = buttons(header(true)).find((x) => x.attrs.includes("Projekt-Session wählen"))
    expect(b).toBeDefined()
    const cls = classOf(b!.attrs)
    expect(cls).toContain("max-w-[140px]")
    expect(cls).toContain("sm:max-w-[240px]")
  })
})

describe("HelpButton auf dem Handy", () => {
  it("zeigt nur das Symbol, Text ab sm, aria-label vorhanden", () => {
    const html = renderToStaticMarkup(<HelpButton topic="chat" />)
    expect(html).toMatch(/<span class="hidden sm:inline">help_label<\/span>/)
    expect(html).toContain('aria-label="help_label"')
  })
})

describe("MessageInput auf dem Handy", () => {
  const input = (withActions = true) => renderToStaticMarkup(
    <MessageInput onSend={() => {}} busy={false}
      quickActions={withActions ? () => <><button type="button">help</button><button type="button">clear</button></> : undefined} />,
  )

  it("Hinweis „Enter zum Senden“ nur ab sm", () => {
    expect(input()).toMatch(/<p class="[^"]*\bhidden\b[^"]*\bsm:block\b[^"]*">input\.hint<\/p>/)
  })

  it("Befehls-Knöpfe in einer wischbaren Zeile ohne Umbruch", () => {
    const row = input().match(/<div class="([^"]*)" data-quick-actions="1">/)
    expect(row).not.toBeNull()
    const cls = row![1].split(" ")
    expect(cls).toEqual(expect.arrayContaining(["flex-nowrap", "overflow-x-auto", "min-w-0"]))
  })

  it("ohne Befehls-Knöpfe keine leere Zeile", () => {
    expect(input(false)).not.toContain('data-quick-actions="1"')
  })
})
