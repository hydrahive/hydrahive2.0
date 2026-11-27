/**
 * TS-Spiegel von agents/area_state.py::toggle (muss sich identisch verhalten): fügt die Tools des Bereichs hinten an (ohne
 * Dubletten) bzw. entfernt genau diese. Alles andere bleibt stehen – Grundausstattung, plugin__/mcp__-Namen, Altbestand und
 * kategorie:x –, Reihenfolge stabil, die Eingabe wird nicht verändert. Gespeichert wird nie „bereich:x“, nur Tool-Namen (E1).
 */
export function toggle(agentTools: string[], areaTools: string[], on: boolean): string[] {
  if (on) {
    const have = new Set(agentTools)
    return [...agentTools, ...areaTools.filter((t, i) => !have.has(t) && areaTools.indexOf(t) === i)]
  }
  const drop = new Set(areaTools)
  return agentTools.filter((t) => !drop.has(t))
}
