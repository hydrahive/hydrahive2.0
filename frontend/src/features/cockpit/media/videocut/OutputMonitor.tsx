import { Film } from "lucide-react"
import { useRef, type CSSProperties } from "react"
import type { MediaTimeline } from "../../mediaWorkspaceApi"
import type { ClipMedia } from "./api"
import { outputLayersAt } from "./assembleOutput"
import { useMediaSync } from "./playbackSync"
import { blackVeilOpacity, overlayStyle } from "./transitions"
import { timecode, type ActiveClip } from "./useCutPlayback"

interface Props {
  timeline: MediaTimeline
  media: Map<string, ClipMedia>
  currentTime: number
  playing: boolean
}

/** <video>-Element, folgt der Master-Clock. key={clip.id} sorgt für Remount bei Clip-Wechsel. */
function VideoSurface({ url, localTime, playing, muted }: { url: string; localTime: number; playing: boolean; muted: boolean }) {
  const ref = useRef<HTMLVideoElement>(null)
  useMediaSync(ref, { localTime, playing, active: true, muted })
  return <video ref={ref} src={url} className="h-full w-full object-contain" playsInline preload="auto" muted={muted} />
}

/** Ein Layer (Video oder Standbild) für einen aktiven Clip. Absolut positioniert,
 *  Effekt-Styling via style. muted, damit im Übergang nicht zwei Tonspuren doppeln
 *  (der Ton kommt aus dem base-Layer / den Audio-Spuren). */
function ClipLayer({ active, media, playing, style, muted }: {
  active: ActiveClip | null
  media: Map<string, ClipMedia>
  playing: boolean
  style?: CSSProperties
  muted: boolean
}) {
  const clipMedia = active ? media.get(active.clip.asset_id) ?? null : null
  if (!active || !clipMedia) return null
  return (
    <div className="absolute inset-0" style={style}>
      {clipMedia.kind === "video" ? (
        <VideoSurface key={active.clip.id} url={clipMedia.url} localTime={active.localTime} playing={playing} muted={muted || active.track.muted} />
      ) : (
        <img key={active.clip.id} src={clipMedia.url} alt="" className="h-full w-full object-contain" />
      )}
    </div>
  )
}

export function OutputMonitor({ timeline, media, currentTime, playing }: Props) {
  const { base, overlay, progress, effect } = outputLayersAt(timeline, currentTime)
  const hasSignal = Boolean(base) || Boolean(overlay)
  const veil = blackVeilOpacity(effect, progress)

  return (
    <div className="flex min-w-0 flex-col">
      <div className="flex items-center justify-between px-1 pb-1">
        <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-[#ffb86b]">Output</span>
        <span className="font-mono text-[10px] text-[#68758a]">{timecode(currentTime)}</span>
      </div>
      <div className="relative aspect-video overflow-hidden rounded-[4px] border border-[#2a364b] bg-black">
        {/* Base-Layer (Spur vor dem Schnittpunkt) — trägt den Ton */}
        <ClipLayer active={base} media={media} playing={playing} muted={false} />

        {/* Overlay-Layer (Spur nach dem Schnittpunkt) — nur im Übergang */}
        {overlay ? <ClipLayer active={overlay} media={media} playing={playing} muted style={overlayStyle(effect, progress)} /> : null}

        {/* Schwarzblende (fade-black) */}
        {veil > 0 ? <div className="pointer-events-none absolute inset-0 bg-black" style={{ opacity: veil }} /> : null}

        {!hasSignal ? (
          <>
            <div className="absolute inset-0 opacity-[0.06]" style={{ backgroundImage: "linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)", backgroundSize: "24px 24px" }} />
            <div className="absolute inset-0 grid place-items-center">
              <div className="flex flex-col items-center gap-1 text-[#3f4b60]">
                <Film size={26} />
                <span className="text-[10px] uppercase tracking-[0.14em]">kein Signal</span>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  )
}
