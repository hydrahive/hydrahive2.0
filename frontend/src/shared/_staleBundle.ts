/* Erkennt, dass dieses Fenster eine ältere Oberfläche zeigt als der Server
   (Befund Till 01.10.2026: nach dem Update fehlten neue Funktionen bis F5).

   Der erste Commit, den /api/health in diesem Fenster meldet, ist der Stand,
   mit dem die Seite geladen wurde. Meldet der Server später einen anderen,
   läuft hier noch die alte Oberfläche. */

export function isStale(loadedWith: string | null, serverNow: string | null): boolean {
  return !!loadedWith && !!serverNow && loadedWith !== serverNow
}
