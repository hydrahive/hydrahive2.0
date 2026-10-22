/** Ergebnis eines Updates aus dem Update-Log ablesen.
 *
 *  installer/update.sh (Linux) und installer/update-mac.sh schreiben als letzte Zeile genau
 *  `HH-UPDATE-ENDE: ok` oder `HH-UPDATE-ENDE: fehler <Grund>` (auch bei Abbruch, per trap).
 *  Vorher wartete das Fenster bis zu 10 Minuten auf einen neuen Commit – bei „nichts Neues“ oder
 *  Abbruch vergeblich (Befund 22.10.2026). Gewertet werden nur Zeilen ab `from` (= Log-Länge beim Start
 *  dieses Laufs), damit die Schlusszeile eines früheren Updates nicht zählt.
 */
export type UpdateOutcome = { kind: "running" } | { kind: "ok" } | { kind: "error"; reason: string }

const MARK = /^HH-UPDATE-ENDE: (ok|fehler)(?: (.*))?$/
// eslint-disable-next-line no-control-regex
const ANSI = /\u001b\[[0-9;]*m/g

export function updateOutcome(lines: string[], from: number): UpdateOutcome {
  for (const raw of lines.slice(Math.max(0, from))) {
    const m = raw.replace(ANSI, "").trim().match(MARK)
    if (!m) continue
    return m[1] === "ok" ? { kind: "ok" } : { kind: "error", reason: (m[2] ?? "").trim() }
  }
  return { kind: "running" }
}
