import { describe, expect, it } from "vitest"
import type { HelpEntry } from "@/i18n/help/loader"
import { orderTopics } from "./helpTopics"

const e = (topic: string, title = topic): HelpEntry => ({ topic, title, source: "core" })

describe("Hilfe-Seite: Themenliste", () => {
  it("Einstieg zuerst, danach der Rest in der gelieferten (alphabetischen) Reihenfolge", () => {
    const list = [e("atelier"), e("buddy"), e("haushaltsbuch"), e("onboarding"), e("zahnfee")]
    expect(orderTopics(list).map((x) => x.topic)).toEqual(["onboarding", "buddy", "atelier", "haushaltsbuch", "zahnfee"])
  })
  it("fehlende Einstiegs-Themen werden übersprungen, nichts doppelt", () => {
    const out = orderTopics([e("buddy"), e("mailbox")]).map((x) => x.topic)
    expect(out).toEqual(["buddy", "mailbox"])
  })
})
