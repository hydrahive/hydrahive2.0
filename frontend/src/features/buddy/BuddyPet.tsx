import { useRive, Layout, Fit, Alignment } from "@rive-app/react-canvas"
import sasquatchUrl from "./animations/sasquatch.riv?url"

export function BuddyPet() {
  const { rive, RiveComponent } = useRive({
    src: sasquatchUrl,
    stateMachines: "State Machine 1",
    autoplay: true,
    layout: new Layout({ fit: Fit.Contain, alignment: Alignment.Center }),
    onLoad: () => console.log("[buddy-pet] loaded"),
    onLoadError: (e) => console.warn("[buddy-pet] load-error", e),
    onStateChange: (e) => console.log("[buddy-pet] state-change", e),
  })

  if (rive && import.meta.env.DEV) {
    console.log("[buddy-pet]",
      "state-machines:", rive.stateMachineNames,
      "animations:", rive.animationNames,
      "inputs:", rive.stateMachineInputs("State Machine 1"))
  }

  return (
    <div className="w-64 h-64 [&_canvas]:!bg-transparent">
      <RiveComponent />
    </div>
  )
}
