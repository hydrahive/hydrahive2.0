import { Film } from "lucide-react"
import { useRef } from "react"
import type { MediaTimeline } from "../../mediaWorkspaceApi"
import type { ClipMedia } from "./api"
import { useMediaSync } from "./playbackSync"
import { clipAt, timecode } from "./useCutPlayback"

interface Props {
  title: string
  /** Video-Spur, an die dieser Monitor gekoppelt ist (vid1 / vid2). */
  trackId: string
  timeline: MediaTimeline
  media: Map<string, ClipMedia>
  /** Playhead-Position (Wiedergabe) in Sekunden. */
  currentTime: number
  /** Roter Cut-Cursor (Justage) in Sekunden. */
  cursorTime: number
  /** Läuft die Wiedergabe? Dann folgt der Monitor dem Playhead, sonst dem Cursor. */
  playing: boolean
  accent: string
}

/** <video>, das der Master-Clock folgt: läuft bei playing, friert sonst am
 *  Sollframe ein. Immer stumm (Ton kommt aus dem Output). */
function VideoSurface({ url, localTime, playing }: { url: string; localTime: number; playing: boolean }) {
  const ref = useRef<HTMLVideoElement>(null)
  useMediaSync(ref, { localTime, playing, active: true, muted: true })
  return <video ref={ref} src={url} className="h-full w-full object-contain" preload="auto" muted playsInline />
}

/** Input-Monitor: zeigt das Frame der gekoppelten Video-Spur. Bei Wiedergabe
 *  läuft er am Playhead mit, sonst friert er am Justage-Cursor ein. */
export function InputMonitor({ title, trackId, timeline, media, currentTime, cursorTime, playing, accent }: Props) {
  const position = playing ? currentTime : cursorTime
  const track = timeline.tracks.find((t) => t.id === trackId)
  const active = track ? clipAt(track, position) : null
  const clipMedia = active ? media.get(active.clip.asset_id) ?? null : null

  return (
    <div className="flex min-w-0 flex-col">
      <div className="flex items-center justify-between px-1 pb-1">
        <span className="font-mono text-[10px] uppercase tracking-[0.14em]" style={{ color: accent }}>{title}</span>
        <span className="font-mono text-[10px] text-[#68758a]">{timecode(position)}</span>
      </div>
      <div className="relative aspect-video overflow-hidden rounded-[4px] border border-[#2a364b] bg-black">
        {clipMedia && clipMedia.kind === "video" ? (
          <VideoSurface key={active!.clip.id} url={clipMedia.url} localTime={active!.localTime + active!.clip.source_in} playing={playing} />
        ) : clipMedia && clipMedia.kind === "image" ? (
          <img key={active!.clip.id} src={clipMedia.url} alt="" className="h-full w-full object-contain" />
        ) : (
          <>
            <div className="absolute inset-0 opacity-[0.06]" style={{ backgroundImage: "linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)", backgroundSize: "24px 24px" }} />
            <div className="absolute inset-0 grid place-items-center">
              <div className="flex flex-col items-center gap-1 text-[#3f4b60]">
                <Film size={26} />
                <span className="text-[10px] uppercase tracking-[0.14em]">kein Signal</span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
