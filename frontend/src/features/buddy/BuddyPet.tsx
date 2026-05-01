import { useRive } from "@rive-app/react-canvas"
import beholderUrl from "./animations/beholder.riv?url"

export function BuddyPet() {
  const { RiveComponent } = useRive({
    src: beholderUrl,
    autoplay: true,
  })

  return (
    <div className="rounded-2xl border border-white/10 bg-zinc-900/50 backdrop-blur p-3 shadow-lg shadow-black/30 flex flex-col items-center gap-2">
      <div className="w-32 h-32">
        <RiveComponent />
      </div>
      <p className="text-[10px] text-zinc-500 font-mono tracking-wide">THE BEHOLDER</p>
    </div>
  )
}
