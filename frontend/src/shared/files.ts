import { useAuthStore } from "@/features/auth/useAuthStore"

/** URL zum Ausliefern einer lokalen Datei über /api/files.
 *
 *  Liegt bewusst im Core: der Endpunkt ist Kern-Infrastruktur und nicht an ein
 *  Modul gebunden. Vorher existierte diese Funktion nur im Atelier-Modul, was
 *  Core-Dateien zu einem Import über die Modulgrenze zwang — und den
 *  Frontend-Build auf jeder Installation ohne Atelier brach.
 *
 *  Der Token wandert in die Query, weil <img>/<video> keine Header setzen können.
 */
export function fileUrl(absPath: string): string {
  const token = useAuthStore.getState().token
  const tokenParam = token ? `&token=${encodeURIComponent(token)}` : ""
  return `/api/files?path=${encodeURIComponent(absPath)}${tokenParam}`
}
