import { describe, expect, it } from "vitest"
import { notImplementedAction } from "./dryRunResult"
import { isNotImplemented } from "./palette-data"

describe("unavailable Butler actions", () => {
  it.each([
    "send_email",
    "git_create_issue",
    "git_add_comment",
    "discord_post",
  ])("marks %s as not implemented in the palette", (subtype) => {
    expect(isNotImplemented(subtype)).toBe(true)
  })

  it("keeps implemented actions available in the palette", () => {
    expect(isNotImplemented("reply_fixed")).toBe(false)
  })
})

describe("notImplementedAction", () => {
  it("returns the unavailable action subtype from a dry-run trace", () => {
    expect(notImplementedAction({
      matched: true,
      actions_executed: [],
      trace: [
        { node_id: "trigger", subtype: "message_received", decision: "match" },
        { node_id: "action", subtype: "send_email", decision: "not_implemented" },
      ],
    })).toBe("send_email")
  })

  it("ignores regular dry-run actions", () => {
    expect(notImplementedAction({
      matched: true,
      actions_executed: [],
      trace: [{ node_id: "action", subtype: "reply_fixed", decision: "would_execute" }],
    })).toBeUndefined()
  })
})
