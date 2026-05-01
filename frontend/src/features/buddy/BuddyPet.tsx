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
    <div className="w-64 h-64 [&_canvas]:!bg-transparent">
      <RiveComponent />
    </div>
  )
}
