import { Film } from "lucide-react"
import { useRef } from "react"
import type { MediaTimeline } from "../../mediaWorkspaceApi"
import type { ClipMedia } from "./api"
import { activeVideoAt } from "./assembleOutput"
import { useMediaSync } from "./playbackSync"
import { timecode } from "./useCutPlayback"

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

export function OutputMonitor({ timeline, media, currentTime, playing }: Props) {
  const active = activeVideoAt(timeline, currentTime)
  const clipMedia = active ? media.get(active.clip.asset_id) ?? null : null

  return (
    <div className="flex min-w-0 flex-col">
      <div className="flex items-center justify-between px-1 pb-1">
        <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-[#ffb86b]">Output</span>
        <span className="font-mono text-[10px] text-[#68758a]">{timecode(currentTime)}</span>
      </div>
      <div className="relative aspect-video overflow-hidden rounded-[4px] border border-[#2a364b] bg-black">
        {clipMedia && clipMedia.kind === "video" ? (
          <VideoSurface
            key={active!.clip.id}
            url={clipMedia.url}
            localTime={active!.localTime}
            playing={playing}
            muted={active!.track.muted}
          />
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
