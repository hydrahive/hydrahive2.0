import { useState } from "react"
import { HydraMascot } from "@/shared/HydraMascot"
import {
  advanceBuddyActionFlow,
  initialBuddyActionFlow,
  syncBuddyActionFlow,
  type BuddyActionPhase,
  type BuddyActivity,
} from "./_buddyActionState"

interface Props {
  activity: BuddyActivity
  speaking: boolean
}

const VIDEOS: Record<BuddyActionPhase, { src: string; label: string; loop: boolean }> = {
  idle: { src: "/buddy/buddy-idle.mp4", label: "Buddy wartet", loop: true },
  starting: { src: "/buddy/buddy-idle-to-working.mp4", label: "Buddy beginnt zu arbeiten", loop: false },
  working: { src: "/buddy/buddy-working.mp4", label: "Buddy arbeitet", loop: true },
  success: { src: "/buddy/buddy-success.mp4", label: "Buddy hat die Aufgabe geschafft", loop: false },
  error: { src: "/buddy/buddy-error.mp4", label: "Bei Buddys Arbeit ist ein Fehler aufgetreten", loop: false },
  stopping: { src: "/buddy/buddy-working-to-idle.mp4", label: "Buddy beendet die Arbeit", loop: false },
}

export function BuddyActionVisual({ activity, speaking }: Props) {
  const [flow, setFlow] = useState(() => initialBuddyActionFlow(activity))

  if (activity !== flow.activity) {
    setFlow(syncBuddyActionFlow(flow, activity))
  }

  if (speaking) {
    return <HydraMascot state="speaking" size={120} animate />
  }

  const video = VIDEOS[flow.phase]
  return (
    <video
      key={video.src}
      src={video.src}
      autoPlay
      loop={video.loop}
      muted
      playsInline
      preload="auto"
      onEnded={video.loop ? undefined : () => setFlow((current) => advanceBuddyActionFlow(current))}
      aria-label={video.label}
      className="h-full w-full object-cover"
    />
  )
}
