export type BuddyActivity = "idle" | "working" | "success" | "error"
export type BuddyActionPhase = "idle" | "starting" | "working" | "success" | "error" | "stopping"

type PendingOutcome = "success" | "error" | "idle" | null

export interface BuddyActionFlow {
  activity: BuddyActivity
  phase: BuddyActionPhase
  pendingOutcome: PendingOutcome
}

export function initialBuddyActionFlow(activity: BuddyActivity): BuddyActionFlow {
  const phase = activity === "working" ? "starting" : activity
  return { activity, phase, pendingOutcome: null }
}

export function syncBuddyActionFlow(flow: BuddyActionFlow, activity: BuddyActivity): BuddyActionFlow {
  if (activity === flow.activity) return flow

  if (activity === "working") {
    return { activity, phase: "starting", pendingOutcome: null }
  }

  if (activity === "success" || activity === "error") {
    if (flow.phase === "starting") {
      return { activity, phase: "starting", pendingOutcome: activity }
    }
    return { activity, phase: activity, pendingOutcome: null }
  }

  if (flow.phase === "starting") {
    return { activity, phase: "starting", pendingOutcome: "idle" }
  }
  if (flow.phase === "working") {
    return { activity, phase: "stopping", pendingOutcome: null }
  }
  if (flow.phase === "success" || flow.phase === "error" || flow.phase === "stopping") {
    return { ...flow, activity }
  }
  return { activity, phase: "idle", pendingOutcome: null }
}

export function advanceBuddyActionFlow(flow: BuddyActionFlow): BuddyActionFlow {
  if (flow.phase === "starting") {
    const phase = flow.pendingOutcome === "idle"
      ? "stopping"
      : flow.pendingOutcome ?? (flow.activity === "working" ? "working" : flow.activity)
    return { ...flow, phase, pendingOutcome: null }
  }
  if (flow.phase === "success" || flow.phase === "error") {
    return { ...flow, phase: "stopping" }
  }
  if (flow.phase === "stopping") {
    return { ...flow, phase: "idle" }
  }
  return flow
}
