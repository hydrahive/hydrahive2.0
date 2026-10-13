/** Größen für das Archiv-Fenster – bis TB (Prod: Projekte bis ~1 TB, Platte 14 TB frei). */
export function formatSize(bytes: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"]
  let value = bytes
  let i = 0
  while (value >= 1024 && i < units.length - 1) { value /= 1024; i++ }
  return i === 0 ? `${value} B` : `${value.toFixed(1)} ${units[i]}`
}

/** Windows-Netzpfad zur Freigabe: \\host\Freigabe */
export function uncPath(host: string, share: string): string {
  return `\\\\${host}\\${share}`
}
