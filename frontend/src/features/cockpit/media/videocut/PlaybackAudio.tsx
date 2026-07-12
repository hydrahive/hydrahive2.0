import { useRef } from "react"
import type { MediaTimeline } from "../../mediaWorkspaceApi"
import type { ClipMedia } from "./api"
import { useMediaSync } from "./playbackSync"
import { clipAt } from "./useCutPlayback"

/** Audio-Spuren des Schnittpults, die parallel zum Output klingen. */
const AUDIO_TRACK_IDS = ["music", "fx", "voice"] as const

interface Props {
  timeline: MediaTimeline
  media: Map<string, ClipMedia>
  currentTime: number
  playing: boolean
}

/** Ein verstecktes <audio> je Spur; folgt der Master-Clock am aktiven Clip. */
function AudioTrackPlayer({ trackId, timeline, media, currentTime, playing }: {
  trackId: string
  timeline: MediaTimeline
  media: Map<string, ClipMedia>
  currentTime: number
  playing: boolean
}) {
  const ref = useRef<HTMLAudioElement>(null)
  const track = timeline.tracks.find((t) => t.id === trackId)
  const active = track ? clipAt(track, currentTime) : null
  const clipMedia = active ? media.get(active.clip.asset_id) ?? null : null

  useMediaSync(ref, {
    localTime: active?.localTime ?? 0,
    playing,
    active: Boolean(clipMedia),
    volume: active?.clip.volume ?? 1,
    muted: track?.muted ?? false,
  })

  // key sorgt für Remount (neue Quelle) bei Clip-Wechsel.
  if (!clipMedia) return null
  return <audio key={active!.clip.id} ref={ref} src={clipMedia.url} preload="auto" />
}

/** Rendert die parallelen Audio-Spuren (Musik/Effekt/Sprache) als versteckte Elemente. */
export function PlaybackAudio({ timeline, media, currentTime, playing }: Props) {
  return (
    <div className="sr-only" aria-hidden>
      {AUDIO_TRACK_IDS.map((id) => (
        <AudioTrackPlayer key={id} trackId={id} timeline={timeline} media={media} currentTime={currentTime} playing={playing} />
      ))}
    </div>
  )
}
