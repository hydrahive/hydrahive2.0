import { Mic, Music, Sparkles, Video } from "lucide-react"
import { useCallback, useMemo, type ComponentType, type PointerEvent } from "react"
import type { MediaAssetReference } from "../../mediaProjectsApi"
import type { MediaTimeline } from "../../mediaWorkspaceApi"
import { ClipBlock } from "./ClipBlock"
import { CutPointMarker } from "./CutPointMarker"
import { TimelineCursors } from "./TimelineCursors"
import { useDragX } from "./useDragX"
import { useElementWidth } from "./useElementWidth"
import { CUT_TRACKS } from "./useCutTimeline"

interface Props {
  timeline: MediaTimeline
  assets: MediaAssetReference[]
  onRemoveClip: (trackId: string, clipId: string) => void
  /** Playhead-Position (Wiedergabe) in Sekunden. */
  currentTime: number
  /** Springt zu Sekunde t (Klick/Scrub im Ruler oder Playhead-Drag). */
  onSeek: (t: number) => void
  /** Wird beim Beginn eines Scrubs gerufen (z.B. um die Wiedergabe zu pausieren). */
  onScrubStart?: () => void
  /** Roter Cut-Cursor (Justage) in Sekunden. */
  cursorTime: number
  onCursorChange: (t: number) => void
  /** Clip-Verschieben: live (preview) + persistiert (commit). */
  onClipPreview: (trackId: string, clipId: string, start: number) => void
  onClipCommit: (trackId: string, clipId: string, start: number) => void
  /** Clip-Trimmen: Kante live (preview) + persistiert (commit). */
  onClipTrimPreview: (trackId: string, clipId: string, edge: "start" | "end", value: number) => void
  onClipTrimCommit: (trackId: string, clipId: string, edge: "start" | "end", value: number) => void
  /** Schnittpunkte: live verschieben (preview) + persistiert (commit) + löschen. */
  onCutPreview: (cutId: string, time: number) => void
  onCutCommit: (cutId: string, time: number) => void
  onCutRemove: (cutId: string) => void
  /** Ausgewählter Schnittpunkt (für Inspector). */
  selectedCutId: string | null
  onSelectCut: (cutId: string) => void
}

const TRACK_META: Record<string, { icon: ComponentType<{ size?: number | string; className?: string }>; tone: string }> = {
  vid1: { icon: Video, tone: "#5aa9ff" },
  vid2: { icon: Video, tone: "#7c9cff" },
  music: { icon: Music, tone: "#4ade80" },
  fx: { icon: Sparkles, tone: "#c084fc" },
  voice: { icon: Mic, tone: "#ffb86b" },
}

const MIN_PX_PER_SECOND = 6   // untere Grenze für lange Filme (dann scrollbar)
const MIN_RULER_SECONDS = 30
const LABEL_COL = 84
const GAP = 8

export function TrackArea({
  timeline, assets, onRemoveClip, currentTime, onSeek, onScrubStart,
  cursorTime, onCursorChange, onClipPreview, onClipCommit,
  onClipTrimPreview, onClipTrimCommit,
  onCutPreview, onCutCommit, onCutRemove, selectedCutId, onSelectCut,
}: Props) {
  const assetLabel = useMemo(() => new Map(assets.map((a) => [a.id, a.label])), [assets])
  const { ref: outerRef, width: outerWidth } = useElementWidth<HTMLDivElement>()

  const totalLen = Math.max(
    MIN_RULER_SECONDS,
    ...timeline.tracks.flatMap((t) => t.clips.map((c) => c.start + c.duration)),
  )
  // Dynamische Skala: Spurbereich füllt die verfügbare Breite; bei langen Filmen
  // greift die Mindest-Skala und die Timeline wird scrollbar.
  const laneWidth = Math.max(0, outerWidth - LABEL_COL - GAP)
  const pxPerSecond = laneWidth > 0 ? Math.max(MIN_PX_PER_SECOND, laneWidth / totalLen) : MIN_PX_PER_SECOND

  const rulerSteps = Math.ceil(totalLen / 5)
  const innerWidth = totalLen * pxPerSecond
  const playheadLeft = Math.min(currentTime, totalLen) * pxPerSecond
  const cursorLeft = Math.min(cursorTime, totalLen) * pxPerSecond

  // Alle Clip-Kanten (Start/Ende) über beide Video-Spuren als Snap-Ziele.
  const clipEdges = useMemo(() => {
    const edges: number[] = [0]
    for (const id of ["vid1", "vid2"]) {
      const track = timeline.tracks.find((t) => t.id === id)
      for (const c of track?.clips ?? []) { edges.push(c.start, c.start + c.duration) }
    }
    return edges
  }, [timeline])

  const cursorDrag = useDragX({ pxPerSecond: pxPerSecond, onMove: onCursorChange })
  const onCursorPointerDown = useCallback((e: PointerEvent) => {
    e.stopPropagation()
    cursorDrag.start(e, cursorTime)
  }, [cursorDrag, cursorTime])

  // Playhead-Drag: pausiert die Wiedergabe und scrubbt über onSeek.
  const playheadDrag = useDragX({ pxPerSecond: pxPerSecond, onMove: onSeek })
  const onPlayheadPointerDown = useCallback((e: PointerEvent) => {
    e.stopPropagation()
    onScrubStart?.()
    playheadDrag.start(e, currentTime)
  }, [playheadDrag, currentTime, onScrubStart])

  const seekFromRuler = useCallback((e: PointerEvent) => {
    onScrubStart?.()
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
    const x = Math.max(0, Math.min(e.clientX - rect.left, innerWidth))
    onSeek(x / pxPerSecond)
  }, [innerWidth, pxPerSecond, onSeek, onScrubStart])

  return (
    <div ref={outerRef} className="overflow-x-auto">
      <div style={{ minWidth: `${innerWidth + LABEL_COL + GAP}px` }}>
        {/* Ruler — Scrub-Fläche (Playhead) */}
        <div className="grid gap-2" style={{ gridTemplateColumns: `${LABEL_COL}px 1fr` }}>
          <div />
          <div
            className="relative h-6 cursor-pointer touch-none rounded-[3px] border border-[#2a364b] bg-[#111827]"
            style={{ width: `${innerWidth}px` }}
            onPointerDown={seekFromRuler}
          >
            {Array.from({ length: rulerSteps + 1 }, (_, i) => (
              <span key={i} className="pointer-events-none absolute top-0.5 font-mono text-[9px] text-[#68758a]" style={{ left: `${i * 5 * pxPerSecond + 2}px` }}>
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
                <div className="flex items-center gap-1.5 rounded-[3px] border border-[#2a364b] bg-[#111827] px-2 py-2" style={{ borderLeft: `3px solid ${meta.tone}` }}>
                  <Icon size={14} className="shrink-0" />
                  <span className="truncate text-[12px] font-semibold text-[#c3ccdd]">{def.name}</span>
                </div>
                <div className="relative h-14 rounded-[3px] border border-[#223048] bg-[#0d1420]" style={{ width: `${innerWidth}px` }}>
                  <div className="absolute inset-0 opacity-[0.04]" style={{ backgroundImage: "linear-gradient(90deg, #fff 1px, transparent 1px)", backgroundSize: `${5 * pxPerSecond}px 100%` }} />
                  {(track?.clips ?? []).map((clip) => (
                    <ClipBlock
                      key={clip.id}
                      clip={clip}
                      label={assetLabel.get(clip.asset_id) ?? clip.asset_id}
                      tone={meta.tone}
                      pxPerSecond={pxPerSecond}
                      snapTargets={def.kind === "video" ? [...clipEdges, cursorTime] : [0, cursorTime]}
                      onPreview={(start) => onClipPreview(def.id, clip.id, start)}
                      onCommit={(start) => onClipCommit(def.id, clip.id, start)}
                      onTrimPreview={(edge, value) => onClipTrimPreview(def.id, clip.id, edge, value)}
                      onTrimCommit={(edge, value) => onClipTrimCommit(def.id, clip.id, edge, value)}
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
              pxPerSecond={pxPerSecond}
              laneOffsetCss={`${LABEL_COL}px + ${GAP}px`}
              snapTargets={clipEdges}
              selected={selectedCutId === cut.id}
              onSelect={() => onSelectCut(cut.id)}
              onPreview={(time) => onCutPreview(cut.id, time)}
              onCommit={(time) => onCutCommit(cut.id, time)}
              onRemove={() => onCutRemove(cut.id)}
            />
          ))}

          <TimelineCursors
            laneOffsetCss={`${LABEL_COL}px + ${GAP}px`}
            playheadLeft={playheadLeft}
            cursorLeft={cursorLeft}
            onPlayheadPointerDown={onPlayheadPointerDown}
            onCursorPointerDown={onCursorPointerDown}
            playheadDragging={playheadDrag.dragging}
            cursorDragging={cursorDrag.dragging}
          />
        </div>
      </div>
    </div>
  )
}
