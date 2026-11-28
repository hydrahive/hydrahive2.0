import { describe, expect, it } from "vitest"
import comDe from "@/i18n/locales/de/communication.json"
import comEn from "@/i18n/locales/en/communication.json"
import chatDe from "@/i18n/locales/de/chat.json"
import chatEn from "@/i18n/locales/en/chat.json"
import helpDe from "@/i18n/help/de/communication.md?raw"
import helpEn from "@/i18n/help/en/communication.md?raw"

// Tasks ff1866f3 + 9b7d0c98: Kanäle landen seit #451 beim Buddy (agents/primary.py), WhatsApp kann Gruppen
// und Sprachnachrichten; der Modell-Picker im Chat gilt nur für die Session, die Sessionliste steht links.
describe("Kommunikations- und Chat-Texte stimmen mit dem Verhalten", () => {
  for (const [lang, com, chat, help] of [["de", comDe, chatDe, helpDe], ["en", comEn, chatEn, helpEn]] as const) {
    it(lang, () => {
      const texts = [com.subtitle, com.whatsapp.description, com.discord.description, help].join(" ")
      expect(texts).not.toMatch(/master/i)
      expect(texts).not.toMatch(/1:1/)
      expect(chat.model_hint).not.toMatch(/alle Sessions|all sessions/i)
      expect(chat.session.select_or_new).not.toMatch(/rechts|right/i)
    })
  }
})
