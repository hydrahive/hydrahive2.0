export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 ** 3) return `${(n / 1024 / 1024).toFixed(1)} MB`
  if (n < 1024 ** 4) return `${(n / 1024 / 1024 / 1024).toFixed(2)} GB`
  return `${(n / 1024 ** 4).toFixed(2)} TB`
}

export function formatRamMB(mb: number): string {
  if (mb < 1024) return `${mb} MB`
  return `${(mb / 1024).toFixed(mb % 1024 === 0 ? 0 : 1)} GB`
}

export function formatRelative(iso: string): string {
  const d = new Date(iso).getTime()
  const diff = Date.now() - d
  if (diff < 60_000) return "gerade eben"
  if (diff < 3_600_000) return `vor ${Math.floor(diff / 60_000)} min`
  if (diff < 86_400_000) return `vor ${Math.floor(diff / 3_600_000)} h`
  return `vor ${Math.floor(diff / 86_400_000)} d`
}
