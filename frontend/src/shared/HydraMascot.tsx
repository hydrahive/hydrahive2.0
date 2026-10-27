import { MASCOT_SRC, type MascotState } from "./mascotSrc"

export type { MascotState }

interface Props {
  state?: MascotState
  size?: number
  animate?: boolean
  className?: string
}

export function HydraMascot({ state = "idle", size = 32, animate = false, className = "" }: Props) {
  return (
    <img
      src={MASCOT_SRC[state]}
      alt=""
      width={size}
      height={size}
      draggable={false}
      className={`object-contain select-none pointer-events-none drop-shadow-[0_3px_8px_rgba(0,0,0,0.45)] ${animate ? "animate-pulse" : ""} ${className}`}
    />
  )
}
