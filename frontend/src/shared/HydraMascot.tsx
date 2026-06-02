export type MascotState =
  | "idle"
  | "working"
  | "speaking"
  | "sleeping"
  | "confused"
  | "celebrate"
  | "thinking"
  | "error"

const SRC: Record<MascotState, string> = {
  idle: "/illustrations/hydra-idle.png",
  working: "/illustrations/hydra-working.png",
  speaking: "/illustrations/hydra-speaking.png",
  sleeping: "/illustrations/hydra-sleeping.png",
  confused: "/illustrations/hydra-confused.png",
  celebrate: "/illustrations/hydra-celebrate.png",
  thinking: "/illustrations/hydra-thinking.png",
  error: "/illustrations/hydra-error.png",
}

interface Props {
  state?: MascotState
  size?: number
  animate?: boolean
  className?: string
}

export function HydraMascot({ state = "idle", size = 32, animate = false, className = "" }: Props) {
  return (
    <img
      src={SRC[state]}
      alt=""
      width={size}
      height={size}
      className={`object-contain select-none pointer-events-none drop-shadow-[0_0_10px_rgba(34,211,238,0.45)] ${animate ? "animate-pulse" : ""} ${className}`}
    />
  )
}
