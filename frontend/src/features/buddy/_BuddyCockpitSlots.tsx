import { ChevronDown, ChevronRight, Eye, EyeOff, Gamepad2, LayoutGrid, Music, Puzzle, PanelRightClose, PanelRightOpen } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { ReactNode } from "react"
import type { BuddyCockpitPrefs, BuddyCockpitSlotId, BuddyDecorVariant } from "./api"

const SLOT_META: Record<BuddyCockpitSlotId, { icon: ReactNode; labelKey: string }> = {
  music: { icon: <Music size={13} />, labelKey: "cockpit.slots.music" },
  extensions: { icon: <Puzzle size={13} />, labelKey: "cockpit.slots.extensions" },
  moduleWidgets: { icon: <Gamepad2 size={13} />, labelKey: "cockpit.slots.moduleWidgets" },
  futureBottom: { icon: <LayoutGrid size={13} />, labelKey: "cockpit.slots.futureBottom" },
}

function SlotCard({
  slot,
  prefs,
  onVisible,
  onCollapsed,
  children,
}: {
  slot: BuddyCockpitSlotId
  prefs: BuddyCockpitPrefs
  onVisible: (slot: BuddyCockpitSlotId, visible: boolean) => void
  onCollapsed: (slot: BuddyCockpitSlotId, collapsed: boolean) => void
  children: ReactNode
}) {
  const { t } = useTranslation("buddy")
  const state = prefs.slots[slot]
  if (!state.visible) return null
  const meta = SLOT_META[slot]
  return (
    <section className="border border-white/[8%] bg-[#1c2334]/90 shadow-lg shadow-black/20">
      <div className="flex items-center gap-2 border-b border-white/[6%] bg-black/25 px-3 py-2 text-xs text-zinc-300">
        <span className="text-sky-300">{meta.icon}</span>
        <span className="font-medium">{t(meta.labelKey)}</span>
        <div className="flex-1" />
        <button
          type="button"
          onClick={() => onCollapsed(slot, !state.collapsed)}
          className="p-1 text-zinc-500 hover:bg-white/[6%] hover:text-zinc-200"
          title={state.collapsed ? t("cockpit.expand") : t("cockpit.collapse")}
        >
          {state.collapsed ? <ChevronRight size={13} /> : <ChevronDown size={13} />}
        </button>
        <button
          type="button"
          onClick={() => onVisible(slot, false)}
          className="p-1 text-zinc-500 hover:bg-white/[6%] hover:text-zinc-200"
          title={t("cockpit.hide")}
        >
          <EyeOff size={13} />
        </button>
      </div>
      {!state.collapsed && <div className="p-2">{children}</div>}
    </section>
  )
}

function SlotToggles({ prefs, onVisible }: { prefs: BuddyCockpitPrefs; onVisible: (slot: BuddyCockpitSlotId, visible: boolean) => void }) {
  const { t } = useTranslation("buddy")
  const hidden = (Object.keys(prefs.slots) as BuddyCockpitSlotId[]).filter((slot) => !prefs.slots[slot].visible)
  if (hidden.length === 0) return null
  return (
    <div className="flex flex-wrap gap-2 border border-white/[8%] bg-black/20 p-2">
      {hidden.map((slot) => (
        <button
          key={slot}
          type="button"
          onClick={() => onVisible(slot, true)}
          className="inline-flex items-center gap-1.5 border border-white/[8%] bg-white/[4%] px-2 py-1 text-[11px] text-zinc-400 hover:text-zinc-100"
        >
          <Eye size={11} /> {t(SLOT_META[slot].labelKey)}
        </button>
      ))}
    </div>
  )
}

export function BuddyCockpitSlots({
  prefs,
  music,
  extensions,
  moduleWidgets,
  onSlotVisible,
  onSlotCollapsed,
  onRightRailCollapsed,
  onDecorVariant,
}: {
  prefs: BuddyCockpitPrefs
  music?: ReactNode
  extensions?: ReactNode
  moduleWidgets?: ReactNode
  onSlotVisible: (slot: BuddyCockpitSlotId, visible: boolean) => void
  onSlotCollapsed: (slot: BuddyCockpitSlotId, collapsed: boolean) => void
  onRightRailCollapsed: (collapsed: boolean) => void
  onDecorVariant: (variant: BuddyDecorVariant) => void
}) {
  const { t } = useTranslation("buddy")
  const decorVariants: BuddyDecorVariant[] = ["default", "calm", "aurora", "minimal"]
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2 border border-white/[8%] bg-[#1c2334]/90 px-3 py-2">
        <button
          type="button"
          onClick={() => onRightRailCollapsed(!prefs.rightRailCollapsed)}
          className="inline-flex items-center gap-1.5 text-[11px] text-zinc-400 hover:text-zinc-100"
        >
          {prefs.rightRailCollapsed ? <PanelRightOpen size={13} /> : <PanelRightClose size={13} />}
          {prefs.rightRailCollapsed ? t("cockpit.show_rail") : t("cockpit.hide_rail")}
        </button>
        <select
          value={prefs.decorVariant}
          onChange={(e) => onDecorVariant(e.target.value as BuddyDecorVariant)}
          className="ml-auto border border-white/[8%] bg-black/30 px-2 py-1 text-[11px] text-zinc-300"
          title={t("cockpit.decor")}
        >
          {decorVariants.map((variant) => (
            <option key={variant} value={variant}>{t(`cockpit.decor_variants.${variant}`)}</option>
          ))}
        </select>
      </div>
      <SlotToggles prefs={prefs} onVisible={onSlotVisible} />
      {music && <SlotCard slot="music" prefs={prefs} onVisible={onSlotVisible} onCollapsed={onSlotCollapsed}>{music}</SlotCard>}
      {extensions && <SlotCard slot="extensions" prefs={prefs} onVisible={onSlotVisible} onCollapsed={onSlotCollapsed}>{extensions}</SlotCard>}
      {moduleWidgets && <SlotCard slot="moduleWidgets" prefs={prefs} onVisible={onSlotVisible} onCollapsed={onSlotCollapsed}>{moduleWidgets}</SlotCard>}
      <SlotCard slot="futureBottom" prefs={prefs} onVisible={onSlotVisible} onCollapsed={onSlotCollapsed}>
        <p className="px-2 py-3 text-xs text-zinc-500">{t("cockpit.slots.future_empty")}</p>
      </SlotCard>
    </div>
  )
}
