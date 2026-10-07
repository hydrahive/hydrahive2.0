// Lebensader zum Backend (Task 06d38ae9): Das Python-Backend startet die Bridge mit stdin als Pipe und schreibt nie
// hinein. Endet das Backend – auch hart per SIGKILL nach einem Stop-Timeout –, schließt das Betriebssystem die Pipe
// und die Bridge bekommt EOF. Dann beendet sie sich selbst, statt als Waise den Port zu blockieren
// (sonst stirbt jede neue Bridge mit EADDRINUSE, weil KillMode=process Kindprozesse bewusst stehen lässt).
// Ohne Pipe (stdin ist ein Terminal, z. B. „npm start“ von Hand) wird nichts überwacht.

export function watchParent(onGone, stdin = process.stdin) {
  if (stdin.isTTY) return false;
  let done = false;
  const gone = () => { if (!done) { done = true; onGone(); } };
  stdin.on("end", gone);
  stdin.on("close", gone);
  stdin.on("error", gone);
  stdin.resume();                      // ohne Lesen kommt kein "end"
  return true;
}
