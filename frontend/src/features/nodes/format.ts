import type { ComputeNode, NodeCapabilities, NodeResources } from "./types"

/** Relative "time ago" in a compact form; falls back to the raw string. */
export function timeAgo(iso: string | null, neverLabel: string): string {
  if (!iso) return neverLabel
  const then = Date.parse(iso)
  if (Number.isNaN(then)) return iso
  const diffMs = Date.now() - then
  const sec = Math.round(diffMs / 1000)
  if (sec < 0) return iso
  if (sec < 60) return `${sec}s`
  const min = Math.round(sec / 60)
  if (min < 60) return `${min}m`
  const hrs = Math.round(min / 60)
  if (hrs < 24) return `${hrs}h`
  const days = Math.round(hrs / 24)
  return `${days}d`
}

export function nodeResources(node: ComputeNode): NodeResources {
  return (node.resources ?? {}) as NodeResources
}

export function nodeCapabilities(node: ComputeNode): NodeCapabilities {
  return (node.capabilities ?? {}) as NodeCapabilities
}

/** Compact local timestamp; falls back to the raw string. */
export function shortDateTime(iso: string | null): string | null {
  if (!iso) return null
  const parsed = Date.parse(iso)
  if (Number.isNaN(parsed)) return iso
  return new Date(parsed).toLocaleString()
}
