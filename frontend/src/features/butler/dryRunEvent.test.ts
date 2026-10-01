import { describe, expect, it } from "vitest"
import { migrateParams } from "./migrateParams"
import { dryRunEvent } from "./dryRunEvent"

describe("dryRunEvent", () => {
  it("builds a message event with the configured channel", () => {
    expect(dryRunEvent("message_received", { channel: "discord" })).toEqual({
      event_type: "message", channel: "discord", message_text: "test",
    })
    expect(dryRunEvent("message_received", {})).toMatchObject({ channel: "all" })
  })

  it("builds a webhook event with its hook ID", () => {
    expect(dryRunEvent("webhook_received", { hook_id: "incoming" })).toEqual({
      event_type: "webhook", payload: { hook_id: "incoming" },
    })
  })

  it("builds a schedule event for heartbeat triggers", () => {
    expect(dryRunEvent("heartbeat_fired", {
      schedule_id: "heartbeat-daily", task_id: "legacy-task", agent_id: "agent-1",
    })).toEqual({
      event_type: "schedule",
      payload: { schedule_id: "heartbeat-daily", task_id: "legacy-task", agent_id: "agent-1" },
    })
  })

  it("builds a schedule event for schedule triggers", () => {
    expect(dryRunEvent("schedule_fired", {
      schedule_id: "interval-1", task_id: "task-1", agent_id: "agent-2",
    })).toEqual({
      event_type: "schedule",
      payload: { schedule_id: "interval-1", task_id: "task-1", agent_id: "agent-2" },
    })
  })

  it("builds a cron event with the optional schedule ID", () => {
    expect(dryRunEvent("cron_fired", { schedule_id: "morning" })).toEqual({
      event_type: "cron", payload: { schedule_id: "morning" },
    })
  })
})

describe("migrateParams", () => {
  it("adopts legacy heartbeat task_id as schedule_id and removes task_id", () => {
    expect(migrateParams("heartbeat_fired", {
      agent_id: "agent-1", task_id: "heartbeat-daily",
    })).toEqual({ agent_id: "agent-1", schedule_id: "heartbeat-daily" })
  })
})
