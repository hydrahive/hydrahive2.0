export function scoreTone(score: number): string {
  if (score >= 80) return "text-emerald-400"
  if (score >= 60) return "text-amber-400"
  return "text-rose-400"
}
