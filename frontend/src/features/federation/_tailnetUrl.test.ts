import { describe, expect, it } from "vitest"
import { isTailnetUrl } from "./_tailnetUrl"

describe("Server koppeln: nur Tailscale-Adressen kommen an", () => {
  it("Tailscale-IPv4 (100.64.0.0/10) und ts.net", () => {
    expect(isTailnetUrl("https://100.93.121.97")).toBe(true)
    expect(isTailnetUrl("https://100.64.0.1:8443/")).toBe(true)
    expect(isTailnetUrl("https://100.127.255.254")).toBe(true)
    expect(isTailnetUrl("https://imac-von-admin.tailabab11.ts.net")).toBe(true)
    expect(isTailnetUrl("https://[fd7a:115c:a1e0::1]")).toBe(true)
  })
  it("Heimnetz und Internet nicht", () => {
    expect(isTailnetUrl("https://192.168.178.186")).toBe(false)
    expect(isTailnetUrl("https://100.63.255.255")).toBe(false)
    expect(isTailnetUrl("https://100.128.0.1")).toBe(false)
    expect(isTailnetUrl("https://10.0.0.5")).toBe(false)
    expect(isTailnetUrl("https://evil.ts.net.example.com")).toBe(false)
    expect(isTailnetUrl("https://ts.net")).toBe(false)
    expect(isTailnetUrl("https://[fd7a:115c:a1e1::1]")).toBe(false)
    expect(isTailnetUrl("kaputt")).toBe(false)
    expect(isTailnetUrl("")).toBe(false)
  })
})
