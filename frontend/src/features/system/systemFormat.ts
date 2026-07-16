export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`
}

export function formatUptime(seconds: number, t: (key: string, options?: Record<string, unknown>) => string): string {
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  if (days > 0) return t("uptime.days_hours", { days, hours })
  const minutes = Math.floor((seconds % 3600) / 60)
  return t("uptime.hours_minutes", { hours, minutes })
}
