// Beschriftung einer Buddy-Unterhaltung in der Auswahl (docs/specs/buddy-session-picker.md).
// Name = erste Nachricht (vom Server gekürzt), dazu Datum. Rein, ohne React → testbar.

export interface LabelInput { first_message: string | null; updated_at: string; message_count: number }

const EMPTY = "(noch leer)"

/** Kurzes Datum: heute → Uhrzeit, dieses Jahr → Tag + Monat, sonst mit Jahr. */
export function shortDate(iso: string, now: Date = new Date(), locale = "de-DE"): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ""
  const sameDay = d.toDateString() === now.toDateString()
  if (sameDay) return d.toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" })
  if (d.getFullYear() === now.getFullYear()) return d.toLocaleDateString(locale, { day: "2-digit", month: "2-digit" })
  return d.toLocaleDateString(locale, { day: "2-digit", month: "2-digit", year: "2-digit" })
}

export function sessionTitle(row: LabelInput): string {
  return row.first_message?.trim() || EMPTY
}

export function sessionMeta(row: LabelInput, now?: Date, locale?: string): string {
  const count = row.message_count === 1 ? "1 Nachricht" : `${row.message_count} Nachrichten`
  return `${shortDate(row.updated_at, now, locale)} · ${count}`
}
