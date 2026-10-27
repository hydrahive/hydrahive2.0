import type { ComponentType } from "react"
import { TileIcon } from "@/shared/brand/TileIcon"

interface Props {
  title: string
  text: string
  onOpen: () => void
  icon: ComponentType<{ size?: number; className?: string }>
  /** Ziel für das Hydra-Bildchen (TILE_ART); ohne: nur das Symbol. */
  art?: string
}

export function AdminInfoCard({ title, text, onOpen, icon: Icon, art }: Props) {
  return (
    <button onClick={onOpen} className="rounded-[4px] border border-[#2a364b] bg-[#111827] p-3 text-left hover:border-[#46617f] hover:bg-[#172133]">
      <div className="mb-2 flex items-center gap-2.5">
        {art ? <TileIcon target={art} icon={Icon} /> : <Icon size={16} className="text-[#69d7ff]" />}
        <h3 className="text-sm font-bold text-[#e8eef8]">{title}</h3>
      </div>
      <p className="text-xs leading-4 text-[#8d9ab0]">{text}</p>
    </button>
  )
}
