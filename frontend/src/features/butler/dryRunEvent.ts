export type DryRunEvent = {
  event_type: string
  channel?: string
  message_text?: string
  payload?: Record<string, unknown>
}

function stringParam(params: Record<string, unknown>, key: string): string | undefined {
  const value = params[key]
  return typeof value === "string" && value ? value : undefined
}

export function dryRunEvent(
  subtype: string,
  params: Record<string, unknown>,
): DryRunEvent {
  switch (subtype) {
    case "webhook_received": {
      const hookId = stringParam(params, "hook_id")
      return { event_type: "webhook", payload: hookId ? { hook_id: hookId } : {} }
    }
    case "heartbeat_fired":
    case "schedule_fired":
      return {
        event_type: "schedule",
        payload: {
          schedule_id: stringParam(params, "schedule_id") ?? stringParam(params, "task_id"),
          task_id: stringParam(params, "task_id"),
          agent_id: stringParam(params, "agent_id"),
        },
      }
    case "cron_fired": {
      const scheduleId = stringParam(params, "schedule_id")
      return { event_type: "cron", payload: scheduleId ? { schedule_id: scheduleId } : {} }
    }
    case "message_received":
    default:
      return {
        event_type: "message",
        channel: stringParam(params, "channel") ?? "all",
        message_text: "test",
      }
  }
}
