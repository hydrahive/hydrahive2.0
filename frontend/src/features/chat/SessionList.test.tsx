import i18next from "i18next"
import { renderToStaticMarkup } from "react-dom/server"
import { I18nextProvider, initReactI18next } from "react-i18next"
import { beforeAll, describe, expect, it } from "vitest"
import de from "@/i18n/locales/de/chat.json"
import { SessionList } from "./SessionList"

const inst = i18next.createInstance()
beforeAll(async () => {
  await inst.use(initReactI18next).init({
    lng: "de", ns: ["chat"], defaultNS: "chat",
    resources: { de: { chat: de } }, interpolation: { escapeValue: false },
  })
})

function html(props: Partial<React.ComponentProps<typeof SessionList>> = {}) {
  return renderToStaticMarkup(
    <I18nextProvider i18n={inst}>
      <SessionList
        sessions={[]} activeId={null} knownAgentIds={new Set()} buddyAgentIds={new Set()} projects={[]}
        onSelect={() => undefined} onDelete={() => undefined} onNew={() => undefined}
        total={73} hasMore loadingMore={false} onLoadMore={() => undefined}
        {...props}
      />
    </I18nextProvider>,
  )
}

describe("SessionList-Pagination", () => {
  it("zeigt Gesamtzahl und sichtbare Ladeaktion", () => {
    const markup = html()

    expect(markup).toContain("73 Sessions")
    expect(markup).toContain("Mehr laden")
  })

  it("deaktiviert die Ladeaktion während des Ladens", () => {
    expect(html({ loadingMore: true })).toMatch(/<button[^>]*disabled[^>]*>.*Lade.*<\/button>/)
  })
})
