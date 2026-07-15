import type { LucideIcon } from "lucide-react"
import { AdminStat } from "@/features/cockpit/admin/ui"

interface Props {
  icon: LucideIcon
  label: string
  value: string | number
  detail?: string
  /** @deprecated Decorative glows are intentionally ignored by the Cockpit visual system. */
  glow?: string
}

export function StatCard({ icon, label, value, detail }: Props) {
  return <AdminStat icon={icon} label={label} value={value} detail={detail} />
}
