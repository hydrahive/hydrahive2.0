import { useRive, useStateMachineInput, Layout, Fit, Alignment } from "@rive-app/react-canvas"
import beholderUrl from "./animations/beholder.riv?url"

export function BuddyPet() {
  const { rive, RiveComponent } = useRive({
    src: beholderUrl,
    stateMachines: "StateMachine1",
    autoplay: true,
    layout: new Layout({ fit: Fit.Contain, alignment: Alignment.Center }),
  })

  const clickInput = useStateMachineInput(rive, "StateMachine1", "mainClick")

  return (
    <div className="rounded-2xl border border-white/10 bg-zinc-900/50 backdrop-blur p-3 shadow-lg shadow-black/30 flex flex-col items-center gap-2">
      <div
        className="w-32 h-32 cursor-pointer"
        onClick={() => clickInput?.fire()}
      >
        <RiveComponent />
      </div>
      <p className="text-[10px] text-zinc-500 font-mono tracking-wide">THE BEHOLDER</p>
    </div>
  )
}
