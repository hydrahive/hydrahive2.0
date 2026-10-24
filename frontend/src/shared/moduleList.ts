/** Modul-Liste aus @/modules/index.generated sicher lesen.
 *
 *  Nur beim Gebrauch aufrufen (in Funktionen/Komponenten), nie auf oberster
 *  Ebene: Importiert ein Modul eine Kern-Datei, ist index.generated beim Laden
 *  dieser Datei noch nicht fertig (Lade-Schleife). Noch nicht gesetzt → [],
 *  statt abzustürzen (Task 08c5c546, docs/specs/modul-ladeschleife.md). */
export function moduleList<T = unknown>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : []
}
