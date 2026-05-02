interface PathRowProps { label: string; value: string }

export function PathRow({ label, value }: PathRowProps) {
  return (
    <div className="flex items-baseline gap-3 text-xs">
      <span className="w-16 text-zinc-500 flex-shrink-0">{label}</span>
      <span className="text-zinc-300 font-mono truncate">{value}</span>
    </div>
  )
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 ** 3) return `${(n / 1024 / 1024).toFixed(1)} MB`
  return `${(n / 1024 ** 3).toFixed(2)} GB`
}

export function formatUptime(
  seconds: number,
  t: (key: string, opts?: Record<string, unknown>) => string,
): string {
  if (seconds < 60) return t("uptime.seconds", { n: Math.floor(seconds) })
  if (seconds < 3600) return t("uptime.minutes", { m: Math.floor(seconds / 60), s: Math.floor(seconds % 60) })
  if (seconds < 86400) return t("uptime.hours", { h: Math.floor(seconds / 3600), m: Math.floor((seconds % 3600) / 60) })
  return t("uptime.days", { d: Math.floor(seconds / 86400), h: Math.floor((seconds % 86400) / 3600) })
}
