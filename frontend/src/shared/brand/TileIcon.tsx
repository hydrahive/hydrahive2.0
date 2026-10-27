import type { ComponentType } from "react"
import { tileArt } from "./tileArt"

interface Props {
  /** Ziel der Kachel (Pfad oder fester Name, siehe TILE_ART). */
  target: string
  /** Bisheriges Symbol – wird gezeigt, wenn es (noch) kein Bildchen gibt. */
  icon: ComponentType<{ size?: number; className?: string }>
  iconClassName?: string
}

/** Bild der Kachel: Hydra-Bildchen (48 px) oder, wenn keins da ist, das bisherige Symbol.
 *  Heller Schein statt dunklem Schatten: dunkle Köpfe (Denker türkis) heben sich so vom dunklen Grund ab. */
export function TileIcon({ target, icon: Icon, iconClassName = "text-[#69d7ff]" }: Props) {
  const src = tileArt(target)
  if (!src) return <Icon size={18} className={iconClassName} />
  return <img src={src} alt="" loading="lazy" draggable={false}
    className="h-12 w-12 shrink-0 select-none object-contain drop-shadow-[0_0_6px_rgba(232,238,248,0.18)]" />
}
