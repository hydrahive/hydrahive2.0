import { useRive, Layout, Fit, Alignment } from "@rive-app/react-canvas"
import sasquatchUrl from "./animations/sasquatch.riv?url"

export function BuddyPet() {
  const { RiveComponent } = useRive({
    src: sasquatchUrl,
    stateMachines: "State Machine 1",
    autoplay: true,
    layout: new Layout({ fit: Fit.Contain, alignment: Alignment.Center }),
  })

  return (
    <div className="rounded-2xl border border-white/10 bg-zinc-900/50 backdrop-blur p-3 shadow-lg shadow-black/30 flex flex-col items-center gap-2">
      <div className="w-40 h-40">
        <RiveComponent />
      </div>
      <p className="text-[10px] text-zinc-500 font-mono tracking-wide">SASQUATCH</p>
    </div>
  )
}
