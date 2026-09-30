import { describe, expect, it, vi } from "vitest"

const get = vi.fn(async (_url: string) => [] as unknown[])
vi.mock("@/shared/api-client", () => ({ api: { get: (url: string) => get(url), post: vi.fn(), delete: vi.fn(), patch: vi.fn() } }))

import { apiKeysApi } from "./api"

describe("apiKeysApi.list", () => {
  it("fragt im Profil nur die eigenen Keys an (mine=true), im Admin-Cockpit alle (Task 9e9439ff)", async () => {
    await apiKeysApi.list(true)
    await apiKeysApi.list()
    expect(get.mock.calls.map((c) => c[0])).toEqual(["/auth/apikeys?mine=true", "/auth/apikeys"])
  })
})
