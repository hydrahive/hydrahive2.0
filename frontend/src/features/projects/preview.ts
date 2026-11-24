// Testseite eines Projekts öffnen (ziele/projekt-testumgebung.md §4, Etappe E1c).
// Die Durchreiche läuft auf Port 8445 desselben Rechners (installer/lib/nginx-project-preview.sh). Der Name kommt aus der
// aktuellen Adresse – so passt es für localhost (WSL), Heimnetz und Tailnet ohne festen Host.
export const PREVIEW_PROXY_PORT = 8445

export function previewLoginUrl(hostname: string, ticket: string): string {
  return `https://${hostname}:${PREVIEW_PROXY_PORT}/__hh_preview_login?t=${encodeURIComponent(ticket)}`
}

interface TabLike { opener: unknown; location: { replace: (url: string) => void }; close: () => void }
type OpenFn = (url: string, target: string) => TabLike | null

/**
 * Popup-Blocker: Chromium und Firefox erlauben window.open nur synchron im Klick. Darum den Tab SOFORT leer öffnen,
 * dann das Ticket holen und erst danach die Adresse setzen. „noopener“ geht dabei nicht als Option (window.open gäbe
 * dann null zurück und der Tab ließe sich nicht mehr lenken) – stattdessen opener von Hand kappen, bevor die fremde
 * Seite lädt. Schlägt das Ticket fehl, wird der leere Tab wieder geschlossen und der Fehler weitergegeben.
 */
export async function openPreviewTab(open: OpenFn, getTicket: () => Promise<{ ticket: string }>,
  hostname: string): Promise<boolean> {
  const tab = open("about:blank", "_blank")
  if (!tab) return false                                   // Popup trotzdem blockiert → Oberfläche zeigt Hinweis
  try {
    const { ticket } = await getTicket()
    tab.opener = null
    tab.location.replace(previewLoginUrl(hostname, ticket))
    return true
  } catch (e) {
    tab.close()
    throw e
  }
}
