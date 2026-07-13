import { useState } from "react"
import { HydraMascot } from "@/shared/HydraMascot"

interface Props {
  state: "idle" | "working" | "speaking"
  animate: boolean
}

export function BuddyActionVisual({ state, animate }: Props) {
  const [transitionComplete, setTransitionComplete] = useState(false)

  if (state === "idle") {
    return (
      <video
        src="/buddy/buddy-idle.mp4"
        autoPlay
        loop
        muted
        playsInline
        preload="auto"
        aria-label="Buddy wartet"
        className="h-full w-full object-cover"
      />
    )
  }

  if (state === "working" && !transitionComplete) {
    return (
      <video
        src="/buddy/buddy-idle-to-working.mp4"
        autoPlay
        muted
        playsInline
        preload="auto"
        onEnded={() => setTransitionComplete(true)}
        aria-label="Buddy beginnt zu arbeiten"
        className="h-full w-full object-cover"
      />
    )
  }

  return <HydraMascot state={state} size={120} animate={animate} />
}
