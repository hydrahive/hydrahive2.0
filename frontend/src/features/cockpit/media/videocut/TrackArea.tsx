import { Mic, Music, Sparkles, Video, X } from "lucide-react"
import { useCallback, useRef, type ComponentType, type PointerEvent } from "react"
import type { MediaAssetReference } from "../../mediaProjectsApi"
import type { MediaTimeline } from "../../mediaWorkspaceApi"
import { CUT_TRACKS } from "./useCutTimeline"

interface Props {
  timeline: MediaTimeline
  assets: MediaAssetReference[]
  onRemoveClip: (trackId: string, clipId: string) => void
  /** Aktuelle Playhead-Position in Sekunden. */
  currentTime: number
  /** Springt zu Sekunde t (Klick/Scrub im Ruler). */
  onSeek: (t: number) => void
}

const TRACK_META: Record<string, { icon: ComponentType<{ size?: number | string; className?: string }>; tone: string }> = {
  vid1: { icon: Video, tone: "#5aa9ff" },
  vid2: { icon: Video, tone: "#7c9cff" },
  music: { icon: Music, tone: "#4ade80" },
  fx: { icon: Sparkles, tone: "#c084fc" },
  voice: { icon: Mic, tone: "#ffb86b" },
}

const PX_PER_SECOND = 6
const MIN_RULER_SECONDS = 30

function fmtDur(s: number): string {
  if (s >= 60) return `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`
  return `${Math.round(s * 10) / 10}s`
}

export function TrackArea({ timeline, assets, onRemoveClip, currentTime, onSeek }: Props) {
  const assetLabel = new Map(assets.map((a) => [a.id, a.label]))
  const totalLen = Math.max(
    MIN_RULER_SECONDS,
    ...timeline.tracks.flatMap((t) => t.clips.map((c) => c.start + c.duration)),
  )
  const rulerSteps = Math.ceil(totalLen / 5)
  const innerWidth = totalLen * PX_PER_SECOND
  const playheadLeft = Math.min(currentTime, totalLen) * PX_PER_SECOND

  const scrubbing = useRef(false)
  const laneRef = useRef<HTMLDivElement>(null)

  const seekFromEvent = useCallback((e: PointerEvent) => {
    const el = laneRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const x = Math.max(0, Math.min(e.clientX - rect.left, innerWidth))
    onSeek(x / PX_PER_SECOND)
  }, [innerWidth, onSeek])

  const onPointerDown = useCallback((e: PointerEvent) => {
    scrubbing.current = true
    e.currentTarget.setPointerCapture(e.pointerId)
    seekFromEvent(e)
  }, [seekFromEvent])

  const onPointerMove = useCallback((e: PointerEvent) => {
    if (scrubbing.current) seekFromEvent(e)
  }, [seekFromEvent])

  const onPointerUp = useCallback((e: PointerEvent) => {
    scrubbing.current = false
    try { e.currentTarget.releasePointerCapture(e.pointerId) } catch { /* nicht gecaptured */ }
  }, [])

  return (
    <div className="overflow-x-auto">
      <div style={{ minWidth: `${innerWidth + 96}px` }}>
        {/* Ruler — Scrub-Fläche */}
        <div className="grid grid-cols-[84px_1fr] gap-2">
          <div />
          <div
            ref={laneRef}
            className="relative h-5 cursor-pointer rounded-[3px] border border-[#2a364b] bg-[#111827] touch-none"
            style={{ width: `${innerWidth}px` }}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
          >
            {Array.from({ length: rulerSteps + 1 }, (_, i) => (
              <span key={i} className="pointer-events-none absolute top-0.5 font-mono text-[9px] text-[#68758a]" style={{ left: `${i * 5 * PX_PER_SECOND + 2}px` }}>
                {i * 5}s
              </span>
            ))}
          </div>
        </div>

        {/* Spuren + Playhead-Overlay */}
        <div className="relative mt-2 space-y-1.5">
          {CUT_TRACKS.map((def) => {
            const track = timeline.tracks.find((t) => t.id === def.id)
            const meta = TRACK_META[def.id]
            const Icon = meta.icon
            return (
              <div key={def.id} className="grid grid-cols-[84px_1fr] gap-2">
                <div className="flex items-center gap-1.5 rounded-[3px] border border-[#2a364b] bg-[#111827] px-2 py-1.5" style={{ borderLeft: `3px solid ${meta.tone}` }}>
                  <Icon size={13} className="shrink-0" />
                  <span className="truncate text-[11px] font-semibold text-[#c3ccdd]">{def.name}</span>
                </div>
                <div className="relative h-10 rounded-[3px] border border-[#223048] bg-[#0d1420]" style={{ width: `${innerWidth}px` }}>
                  <div className="absolute inset-0 opacity-[0.04]" style={{ backgroundImage: "linear-gradient(90deg, #fff 1px, transparent 1px)", backgroundSize: `${5 * PX_PER_SECOND}px 100%` }} />
                  {(track?.clips ?? []).map((clip) => (
                    <div key={clip.id}
                      className="group absolute inset-y-1 overflow-hidden rounded-[3px] border px-1.5 py-0.5"
                      style={{
                        left: `${clip.start * PX_PER_SECOND}px`,
                        width: `${Math.max(clip.duration * PX_PER_SECOND, 34)}px`,
                        borderColor: meta.tone,
                        background: `${meta.tone}22`,
                      }}
                      title={`${assetLabel.get(clip.asset_id) ?? clip.asset_id} · ${fmtDur(clip.duration)}`}>
                      <p className="truncate text-[9px] font-semibold leading-3 text-[#e8eef8]">{assetLabel.get(clip.asset_id) ?? clip.asset_id}</p>
                      <p className="font-mono text-[8px] text-[#8d9ab0]">{fmtDur(clip.duration)}</p>
                      <button onClick={() => onRemoveClip(def.id, clip.id)} aria-label="Clip entfernen"
                        className="absolute right-0.5 top-0.5 hidden rounded-[2px] bg-black/60 p-0.5 text-zinc-300 hover:text-white group-hover:block">
                        <X size={9} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}

          {/* Playhead-Linie über allen Spuren (nur im Spurbereich, nicht über den Labels) */}
          <div
            className="pointer-events-none absolute inset-y-0 z-10 w-px bg-[#ffb86b]"
            style={{ left: `calc(84px + 0.5rem + ${playheadLeft}px)` }}
          >
            <div className="absolute -top-0.5 -left-[3px] h-1.5 w-1.5 rounded-full bg-[#ffb86b]" />
          </div>
        </div>
      </div>
    </div>
  )
}
