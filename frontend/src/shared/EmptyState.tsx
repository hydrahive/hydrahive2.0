import { MASCOT_SRC, type MascotState } from "./mascotSrc"

interface Props {
  /** Stimmung der bunten Hydra (public/hydra/), z. B. „sleeping“ für „noch nichts da“, „confused“ für 404. */
  mood?: MascotState
  /** Eigenes Bild (für Module, die EmptyState so schon nutzen). Hat Vorrang vor mood. */
  src?: string
  title?: string
  hint?: React.ReactNode
  size?: number
  className?: string
  children?: React.ReactNode
}

/** Leer-Zustand mit Tills bunter Hydra (Task 0dda5420). */
export function EmptyState({ mood = "idle", src, title, hint, size = 112, className = "", children }: Props) {
  return (
    <div className={`flex flex-col items-center justify-center text-center gap-2.5 py-8 px-6 ${className}`}>
      <img
        src={src ?? MASCOT_SRC[mood]}
        alt=""
        width={size}
        height={size}
        loading="lazy"
        draggable={false}
        className="object-contain select-none pointer-events-none drop-shadow-[0_6px_16px_rgba(0,0,0,0.45)]"
      />
      {title && <p className="text-sm font-medium text-zinc-300">{title}</p>}
      {hint && <p className="text-xs text-zinc-500 max-w-[22rem] leading-relaxed">{hint}</p>}
      {children}
    </div>
  )
}
