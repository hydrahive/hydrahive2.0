import type { ComponentType } from "react"
import { tileArt } from "./tileArt"

interface Props {
  /** Ziel der Kachel (Pfad oder fester Name, siehe TILE_ART). */
  target: string
  /** Bisheriges Symbol – wird gezeigt, wenn es (noch) kein Bildchen gibt. */
  icon: ComponentType<{ size?: number; className?: string }>
  iconClassName?: string
  /** md = 48 px (Kacheln), sm = 28 px (passt in ein 32-px-Feld mit Rand, z. B. Medien-Schritte). */
  size?: "md" | "sm"
  /** Symbolgröße im Rückfall. */
  iconSize?: number
}

const IMG = { md: "h-12 w-12", sm: "h-7 w-7" } as const

/** Bild der Kachel: Hydra-Bildchen oder, wenn keins da ist, das bisherige Symbol.
 *  Heller Schein statt dunklem Schatten: dunkle Köpfe (Denker türkis) heben sich so vom dunklen Grund ab. */
export function TileIcon({ target, icon: Icon, iconClassName = "text-[#69d7ff]", size = "md", iconSize = 18 }: Props) {
  const src = tileArt(target)
  if (!src) return <Icon size={iconSize} className={iconClassName} />
  return <img src={src} alt="" loading="lazy" draggable={false}
    className={`${IMG[size]} shrink-0 select-none object-contain drop-shadow-[0_0_6px_rgba(232,238,248,0.18)]`} />
}
