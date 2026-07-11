import { Mic, Music, Sparkles, Video, X } from "lucide-react"
import type { ComponentType } from "react"
import type { MediaAssetReference } from "../../mediaProjectsApi"
import type { MediaTimeline } from "../../mediaWorkspaceApi"
import { CUT_TRACKS } from "./useCutTimeline"

interface Props {
  timeline: MediaTimeline
  assets: MediaAssetReference[]
  onRemoveClip: (trackId: string, clipId: string) => void
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

export function TrackArea({ timeline, assets, onRemoveClip }: Props) {
  const assetLabel = new Map(assets.map((a) => [a.id, a.label]))
  const totalLen = Math.max(
    MIN_RULER_SECONDS,
    ...timeline.tracks.flatMap((t) => t.clips.map((c) => c.start + c.duration)),
  )
  const rulerSteps = Math.ceil(totalLen / 5)
  const innerWidth = totalLen * PX_PER_SECOND

  return (
    <div className="overflow-x-auto">
      <div style={{ minWidth: `${innerWidth + 96}px` }}>
        {/* Ruler */}
        <div className="grid grid-cols-[84px_1fr] gap-2">
          <div />
          <div className="relative h-5 rounded-[3px] border border-[#2a364b] bg-[#111827]" style={{ width: `${innerWidth}px` }}>
            {Array.from({ length: rulerSteps + 1 }, (_, i) => (
              <span key={i} className="absolute top-0.5 font-mono text-[9px] text-[#68758a]" style={{ left: `${i * 5 * PX_PER_SECOND + 2}px` }}>
                {i * 5}s
              </span>
            ))}
          </div>
        </div>

        {/* Spuren */}
        <div className="mt-2 space-y-1.5">
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
        </div>
      </div>
    </div>
  )
}
