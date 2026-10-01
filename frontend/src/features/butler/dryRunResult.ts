export type DryRunTrace = {
  node_id: string
  subtype: string
  decision: string
}

export type DryRunResult = {
  matched: boolean
  actions_executed: { subtype: string }[]
  trace: DryRunTrace[]
}

export function notImplementedAction(result: DryRunResult): string | undefined {
  return result.trace.find((item) => item.decision === "not_implemented")?.subtype
}
