import { useState } from "react"
import { Grid3X3, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { NAV_GROUPS, visibleItems } from "@/shared/nav-config"

const go = (path: string) => window.open(path, "_self")

export function CockpitAppsMenu({ compact = false }: { compact?: boolean }) {
  const [open, setOpen] = useState(false)
  const role = useAuthStore((state) => state.role)
  const { t } = useTranslation("nav")
  const items = visibleItems(role).filter((item) => item.path !== "/help")

  return <div className="relative">
    <button onClick={() => setOpen((value) => !value)} aria-expanded={open} aria-controls="cockpit-apps-menu" className={compact ? "flex w-full items-center gap-2 rounded-[4px] border border-[#2a364b] bg-[#172133] px-3 py-2 text-xs font-bold text-[#e8eef8]" : "rounded-[4px] border border-[#2a364b] bg-[#172133] p-2 text-[#e8eef8] hover:border-[#46617f]"} title="Apps"><Grid3X3 size={16} />{compact && <span>Apps</span>}</button>
    {open && <><button className="fixed inset-0 z-[119] cursor-default bg-black/40" aria-label="Apps schließen" onClick={() => setOpen(false)} /><section id="cockpit-apps-menu" role="dialog" aria-label="Apps" className="fixed inset-x-3 top-[68px] z-[120] max-h-[calc(100dvh-80px)] overflow-y-auto rounded-[6px] border border-[#2a364b] bg-[#101724] p-4 shadow-2xl sm:absolute sm:inset-x-auto sm:right-0 sm:top-11 sm:w-[520px]"><header className="mb-3 flex items-center justify-between"><div><p className="text-xs uppercase tracking-wider text-[#718097]">HydraHive</p><h2 className="font-semibold text-[#e8eef8]">Apps</h2></div><button onClick={() => setOpen(false)} className="rounded p-2 text-[#8d9ab0] hover:bg-white/5 hover:text-white" aria-label="Apps schließen"><X size={17} /></button></header>{NAV_GROUPS.map((group) => { const grouped = items.filter((item) => item.group === group.key); if (!grouped.length) return null; return <div key={group.key} className="mb-4 last:mb-0"><p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-[#718097]">{t(group.labelKey)}</p><div className="grid grid-cols-2 gap-1 sm:grid-cols-3">{grouped.map((item) => <button key={item.path} onClick={() => go(item.path)} className="flex min-w-0 items-center gap-2 rounded-[4px] border border-transparent px-2 py-2 text-left text-xs text-[#b8c4d8] hover:border-[#2a364b] hover:bg-[#172133] hover:text-white"><item.icon size={14} className="shrink-0 text-[#69d7ff]" /><span className="truncate">{t(item.labelKey)}</span></button>)}</div></div> })}</section></>}
  </div>
}
