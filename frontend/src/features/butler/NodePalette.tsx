/**
 * Linke Sidebar des Butler-Editors — Drag-Source für die drei
 * Node-Gruppen Trigger / Condition / Action. Jede Gruppe ist
 * collapsible. Items werden via dataTransfer mit MIME-Type
 * "application/butler-node" auf den Canvas gezogen.
 */
import React, { useMemo } from "react"
import type { CSSProperties } from "react"
import { useTranslation } from "react-i18next"
import { cn } from "@/shared/cn"
import { PALETTE_LABEL_KEY, PALETTE_STRUCTURE, UNWIRED_TRIGGERS } from "./palette-data"
import { rgbFor } from "@/shared/colors"

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
    <div className="box overflow-y-auto w-44 shrink-0 p-3 flex flex-col gap-2" style={{ "--c": rgbFor("/butler") } as CSSProperties}>
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
                  const unwired = UNWIRED_TRIGGERS.has(item.subtype)
                  return (
                    <div
                      key={item.subtype}
                      title={unwired ? t("node_unwired") : undefined}
                      className={cn(
                        "relative flex items-center gap-2 rounded-lg border px-2 py-1.5 text-xs transition-colors",
                        unwired
                          ? "cursor-not-allowed border-zinc-700/50 bg-zinc-900/50 text-zinc-500"
                          : cn("cursor-grab active:cursor-grabbing", COLOR_MAP[group.color]),
                      )}
                      draggable={!unwired}
                      onDragStart={unwired ? undefined : (e) => onDragStart(e, item)}
                    >
                      <Icon className="h-3.5 w-3.5 shrink-0" />
                      <span className="truncate leading-tight">{item.label}</span>
                      {unwired && (
                        <span className="ml-auto shrink-0 rounded px-1 py-0.5 text-[9px] font-semibold bg-amber-900/60 text-amber-400 border border-amber-700/40">
                          bald
                        </span>
                      )}
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
