/**
 * Linke Sidebar des Butler-Editors — Drag-Source für die drei
 * Node-Gruppen Trigger / Condition / Action. Jede Gruppe ist
 * collapsible. Items werden via dataTransfer mit MIME-Type
 * "application/butler-node" auf den Canvas gezogen.
 */
import React, { useMemo } from "react"
import { useTranslation } from "react-i18next"
import { cn } from "@/shared/cn"
import { PALETTE_LABEL_KEY, PALETTE_STRUCTURE } from "./palette-data"

const COLOR_MAP = {
  green:  "border-green-500/40 bg-green-950/30 hover:bg-green-950/60 text-green-300",
  blue:   "border-blue-500/40 bg-blue-950/30 hover:bg-blue-950/60 text-blue-300",
  orange: "border-orange-500/40 bg-orange-950/30 hover:bg-orange-950/60 text-orange-300",
} as const

const HEADER_COLOR = {
  green:  "text-green-400/70 hover:text-green-300",
  blue:   "text-blue-400/70 hover:text-blue-300",
  orange: "text-orange-400/70 hover:text-orange-300",
} as const

export function NodePalette() {
  const { t } = useTranslation("butler")
  const [open, setOpen] = React.useState<Record<string, boolean>>({
    groupTrigger: true, groupCondition: false, groupAction: false,
  })

  const onDragStart = (
    event: React.DragEvent,
    item: { type: string; subtype: string; label: string },
  ) => {
    event.dataTransfer.setData("application/butler-node", JSON.stringify(item))
    event.dataTransfer.effectAllowed = "move"
  }

  const palette = useMemo(() => PALETTE_STRUCTURE.map((group) => ({
    group: t(group.groupKey),
    groupKey: group.groupKey,
    color: group.color,
    items: group.items.map((item) => ({
      ...item,
      label: t(PALETTE_LABEL_KEY[item.subtype] || item.subtype),
    })),
  })), [t])

  return (
    <div className="w-44 shrink-0 overflow-y-auto border-r border-white/10 bg-[hsl(var(--sidebar-bg,220_15%_8%))] p-3 flex flex-col gap-2">
      <p className="text-[0.6rem] font-semibold uppercase tracking-[0.18em] text-white/30 px-1 mb-1">
        {t("nodePalette")}
      </p>
      {palette.map((group) => {
        const isOpen = open[group.groupKey] ?? true
        return (
          <div key={group.groupKey}>
            <button
              type="button"
              onClick={() => setOpen((prev) => ({ ...prev, [group.groupKey]: !isOpen }))}
              className={cn(
                "w-full flex items-center justify-between px-1 py-1 text-[0.55rem] font-bold uppercase tracking-widest transition-colors",
                HEADER_COLOR[group.color],
              )}
            >
              <span>{group.group}</span>
              <span className="text-white/20">{isOpen ? "▲" : "▼"}</span>
            </button>
            {isOpen && (
              <div className="flex flex-col gap-1.5 mt-1">
                {group.items.map((item) => {
                  const Icon = item.icon
                  return (
                    <div
                      key={item.subtype}
                      className={cn(
                        "flex items-center gap-2 rounded-lg border px-2 py-1.5 text-xs",
                        "cursor-grab active:cursor-grabbing transition-colors",
                        COLOR_MAP[group.color],
                      )}
                      draggable
                      onDragStart={(e) => onDragStart(e, item)}
                    >
                      <Icon className="h-3.5 w-3.5 shrink-0" />
                      <span className="truncate leading-tight">{item.label}</span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
      <div className="mt-auto pt-3 border-t border-white/10">
        <p className="text-[0.55rem] text-white/20 leading-relaxed px-1">
          {t("paletteDragHint")}
        </p>
      </div>
    </div>
  )
}
