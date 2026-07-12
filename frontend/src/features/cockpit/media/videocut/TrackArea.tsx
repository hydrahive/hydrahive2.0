import { Mic, Music, Sparkles, Video } from "lucide-react"
import { useCallback, useMemo, type ComponentType, type PointerEvent } from "react"
import type { MediaAssetReference } from "../../mediaProjectsApi"
import type { MediaTimeline } from "../../mediaWorkspaceApi"
import { ClipBlock } from "./ClipBlock"
import { CutPointMarker } from "./CutPointMarker"
import { useDragX } from "./useDragX"
import { CUT_TRACKS } from "./useCutTimeline"

interface Props {
  timeline: MediaTimeline
  assets: MediaAssetReference[]
  onRemoveClip: (trackId: string, clipId: string) => void
  /** Playhead-Position (Wiedergabe) in Sekunden. */
  currentTime: number
  /** Springt zu Sekunde t (Klick/Scrub im Ruler). */
  onSeek: (t: number) => void
  /** Roter Cut-Cursor (Justage) in Sekunden. */
  cursorTime: number
  onCursorChange: (t: number) => void
  /** Clip-Verschieben: live (preview) + persistiert (commit). */
  onClipPreview: (trackId: string, clipId: string, start: number) => void
  onClipCommit: (trackId: string, clipId: string, start: number) => void
  /** Schnittpunkte: live verschieben (preview) + persistiert (commit) + löschen. */
  onCutPreview: (cutId: string, time: number) => void
  onCutCommit: (cutId: string, time: number) => void
  onCutRemove: (cutId: string) => void
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
const LABEL_COL = 84
const GAP = 8

export function TrackArea({
  timeline, assets, onRemoveClip, currentTime, onSeek,
  cursorTime, onCursorChange, onClipPreview, onClipCommit,
  onCutPreview, onCutCommit, onCutRemove,
}: Props) {
  const assetLabel = useMemo(() => new Map(assets.map((a) => [a.id, a.label])), [assets])
  const totalLen = Math.max(
    MIN_RULER_SECONDS,
    ...timeline.tracks.flatMap((t) => t.clips.map((c) => c.start + c.duration)),
  )
  const rulerSteps = Math.ceil(totalLen / 5)
  const innerWidth = totalLen * PX_PER_SECOND
  const playheadLeft = Math.min(currentTime, totalLen) * PX_PER_SECOND
  const cursorLeft = Math.min(cursorTime, totalLen) * PX_PER_SECOND

  // Alle Clip-Kanten (Start/Ende) über beide Video-Spuren als Snap-Ziele.
  const clipEdges = useMemo(() => {
    const edges: number[] = [0]
    for (const id of ["vid1", "vid2"]) {
      const track = timeline.tracks.find((t) => t.id === id)
      for (const c of track?.clips ?? []) { edges.push(c.start, c.start + c.duration) }
    }
    return edges
  }, [timeline])

  const cursorDrag = useDragX({ pxPerSecond: PX_PER_SECOND, onMove: onCursorChange })
  const onCursorPointerDown = useCallback((e: PointerEvent) => {
    e.stopPropagation()
    cursorDrag.start(e, cursorTime)
  }, [cursorDrag, cursorTime])

  const seekFromRuler = useCallback((e: PointerEvent) => {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
    const x = Math.max(0, Math.min(e.clientX - rect.left, innerWidth))
    onSeek(x / PX_PER_SECOND)
  }, [innerWidth, onSeek])

  return (
    <div className="overflow-x-auto">
      <div style={{ minWidth: `${innerWidth + LABEL_COL + GAP}px` }}>
        {/* Ruler — Scrub-Fläche (Playhead) */}
        <div className="grid gap-2" style={{ gridTemplateColumns: `${LABEL_COL}px 1fr` }}>
          <div />
          <div
            className="relative h-5 cursor-pointer touch-none rounded-[3px] border border-[#2a364b] bg-[#111827]"
            style={{ width: `${innerWidth}px` }}
            onPointerDown={seekFromRuler}
          >
            {Array.from({ length: rulerSteps + 1 }, (_, i) => (
              <span key={i} className="pointer-events-none absolute top-0.5 font-mono text-[9px] text-[#68758a]" style={{ left: `${i * 5 * PX_PER_SECOND + 2}px` }}>
                {i * 5}s
              </span>
            ))}
          </div>
        </div>

        {/* Spuren + Overlays (Playhead + roter Cut-Cursor) */}
        <div className="relative mt-2 space-y-1.5">
          {CUT_TRACKS.map((def) => {
            const track = timeline.tracks.find((t) => t.id === def.id)
            const meta = TRACK_META[def.id]
            const Icon = meta.icon
            return (
              <div key={def.id} className="grid gap-2" style={{ gridTemplateColumns: `${LABEL_COL}px 1fr` }}>
                <div className="flex items-center gap-1.5 rounded-[3px] border border-[#2a364b] bg-[#111827] px-2 py-1.5" style={{ borderLeft: `3px solid ${meta.tone}` }}>
                  <Icon size={13} className="shrink-0" />
                  <span className="truncate text-[11px] font-semibold text-[#c3ccdd]">{def.name}</span>
                </div>
                <div className="relative h-10 rounded-[3px] border border-[#223048] bg-[#0d1420]" style={{ width: `${innerWidth}px` }}>
                  <div className="absolute inset-0 opacity-[0.04]" style={{ backgroundImage: "linear-gradient(90deg, #fff 1px, transparent 1px)", backgroundSize: `${5 * PX_PER_SECOND}px 100%` }} />
                  {(track?.clips ?? []).map((clip) => (
                    <ClipBlock
                      key={clip.id}
                      clip={clip}
                      label={assetLabel.get(clip.asset_id) ?? clip.asset_id}
                      tone={meta.tone}
                      pxPerSecond={PX_PER_SECOND}
                      snapTargets={def.kind === "video" ? [...clipEdges, cursorTime] : [0, cursorTime]}
                      onPreview={(start) => onClipPreview(def.id, clip.id, start)}
                      onCommit={(start) => onClipCommit(def.id, clip.id, start)}
                      onRemove={() => onRemoveClip(def.id, clip.id)}
                    />
                  ))}
                </div>
              </div>
            )
          })}

          {/* Schnittpunkt-Marker (weiß, ziehbar) */}
          {(timeline.cut_points ?? []).map((cut) => (
            <CutPointMarker
              key={cut.id}
              cut={cut}
              pxPerSecond={PX_PER_SECOND}
              laneOffsetCss={`${LABEL_COL}px + ${GAP}px`}
              snapTargets={clipEdges}
              onPreview={(time) => onCutPreview(cut.id, time)}
              onCommit={(time) => onCutCommit(cut.id, time)}
              onRemove={() => onCutRemove(cut.id)}
            />
          ))}

          {/* Playhead-Linie (Wiedergabe) */}
          <div
            className="pointer-events-none absolute inset-y-0 z-10 w-px bg-[#ffb86b]"
            style={{ left: `calc(${LABEL_COL}px + ${GAP}px + ${playheadLeft}px)` }}
          >
            <div className="absolute -top-0.5 -left-[3px] h-1.5 w-1.5 rounded-full bg-[#ffb86b]" />
          </div>

          {/* Roter Cut-Cursor (Justage) — ziehbar */}
          <div
            className="absolute inset-y-0 z-20 w-[2px] touch-none bg-rose-500"
            style={{ left: `calc(${LABEL_COL}px + ${GAP}px + ${cursorLeft}px)` }}
          >
            <div
              onPointerDown={onCursorPointerDown}
              className={["absolute -top-1 -left-[6px] h-3 w-3.5 cursor-ew-resize rounded-[2px] bg-rose-500 shadow",
                cursorDrag.dragging ? "ring-2 ring-rose-300" : ""].join(" ")}
              title="Cut-Cursor ziehen"
            />
          </div>
        </div>
      </div>
    </div>
  )
}
