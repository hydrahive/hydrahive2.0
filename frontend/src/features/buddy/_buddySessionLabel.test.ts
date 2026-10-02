import { describe, expect, it } from "vitest"
import { sessionMeta, sessionTitle, shortDate } from "./_buddySessionLabel"

const now = new Date("2026-10-02T23:30:00")

describe("Beschriftung der Buddy-Unterhaltungen", () => {
  it("heute zeigt die Uhrzeit, dieses Jahr Tag und Monat, früher mit Jahr", () => {
    expect(shortDate("2026-10-02T17:03:00", now)).toBe("17:03")
    expect(shortDate("2026-06-15T10:00:00", now)).toBe("15.06.")
    expect(shortDate("2025-12-24T10:00:00", now)).toBe("24.12.25")
  })

  it("ungültiges Datum ergibt leeren Text statt „Invalid Date“", () => {
    expect(shortDate("kaputt", now)).toBe("")
  })

  it("Titel ist die erste Nachricht, leere Unterhaltung bekommt einen Hinweis", () => {
    expect(sessionTitle({ first_message: "Wie war mein Blutdruck?", updated_at: "", message_count: 3 })).toBe("Wie war mein Blutdruck?")
    expect(sessionTitle({ first_message: null, updated_at: "", message_count: 0 })).toBe("(noch leer)")
    expect(sessionTitle({ first_message: "   ", updated_at: "", message_count: 0 })).toBe("(noch leer)")
  })

  it("Zusatzzeile mit Datum und Anzahl, Einzahl richtig", () => {
    expect(sessionMeta({ first_message: "x", updated_at: "2026-10-02T09:13:00", message_count: 1 }, now)).toBe("09:13 · 1 Nachricht")
    expect(sessionMeta({ first_message: "x", updated_at: "2026-09-12T19:13:00", message_count: 4749 }, now)).toBe("12.09. · 4749 Nachrichten")
  })
})
