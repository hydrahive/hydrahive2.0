/** Gewählter Agent/Projekt in „Meine Einstellungen“ steht in der URL (`?item=<id>`). */
export function selectedItem(search: string): string | null {
  return new URLSearchParams(search).get("item")
}

/** Neue Suchzeichenkette mit (oder ohne) Auswahl; andere Parameter bleiben. */
export function withItem(search: string, id: string | null): string {
  const p = new URLSearchParams(search)
  if (id) p.set("item", id)
  else p.delete("item")
  const s = p.toString()
  return s ? `?${s}` : ""
}
