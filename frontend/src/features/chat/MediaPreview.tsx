/**
 * Erkennt Bild/Audio/Video-URLs in beliebigem Text und rendert sie als
 * Player. Genutzt in ToolResultCard (DevChat) und BuddyBubble.
 */

// HTTP(S)-URLs
const IMG_RE = /(https?:\/\/[^\s)]+\.(?:png|jpe?g|gif|webp|svg|bmp|avif))(?:\?[^\s)]*)?/gi
const AUD_RE = /(https?:\/\/[^\s)]+\.(?:mp3|ogg|wav|m4a|opus|flac))(?:\?[^\s)]*)?/gi
const VID_RE = /(https?:\/\/[^\s)]+\.(?:mp4|webm|mov|m3u8))(?:\?[^\s)]*)?/gi
// Absolute Filesystem-Pfade (z.B. /tmp/foo.png aus generierten Tool-Results) —
// werden via /api/files?path= an das Backend delegiert.
// Kein Pre-Anker — Pfade sollen auch in JSON-Strings (Tool-Results) gefunden
// werden, wo " direkt vorm / steht: `"output_file": "/tmp/foo.jpg"`.
// Stopp-Zeichen am Ende: Whitespace, `, ), ", ', ], }, ,
const ABS_IMG_RE = /(\/(?:tmp|var\/lib\/hydrahive2)\/[^\s`)"'\],}]+\.(?:png|jpe?g|gif|webp|svg|bmp|avif))/gi
const ABS_AUD_RE = /(\/(?:tmp|var\/lib\/hydrahive2)\/[^\s`)"'\],}]+\.(?:mp3|ogg|wav|m4a|opus|flac))/gi
const ABS_VID_RE = /(\/(?:tmp|var\/lib\/hydrahive2)\/[^\s`)"'\],}]+\.(?:mp4|webm|mov|m3u8))/gi

function toApiUrl(path: string): string {
  return `/api/files?path=${encodeURIComponent(path)}`
}

function matchAll(text: string, re: RegExp): string[] {
  const out: string[] = []
  let m: RegExpExecArray | null
  re.lastIndex = 0
  while ((m = re.exec(text)) !== null) out.push(m[1] || m[0])
  return out
}

export interface ExtractedMedia {
  images: string[]
  audio: string[]
  videos: string[]
}

export function extractMedia(text: string): ExtractedMedia {
  if (!text) return { images: [], audio: [], videos: [] }
  const dedupe = (xs: string[]) => Array.from(new Set(xs))
  const images = [
    ...(text.match(IMG_RE) || []),
    ...matchAll(text, ABS_IMG_RE).map(toApiUrl),
  ]
  const audio = [
    ...(text.match(AUD_RE) || []),
    ...matchAll(text, ABS_AUD_RE).map(toApiUrl),
  ]
  const videos = [
    ...(text.match(VID_RE) || []),
    ...matchAll(text, ABS_VID_RE).map(toApiUrl),
  ]
  return { images: dedupe(images), audio: dedupe(audio), videos: dedupe(videos) }
}

export function hasMedia(text: string): boolean {
  const m = extractMedia(text)
  return m.images.length + m.audio.length + m.videos.length > 0
}

export function MediaPreview({ media }: { media: ExtractedMedia }) {
  if (media.images.length + media.audio.length + media.videos.length === 0) return null
  return (
    <div className="space-y-2">
      {media.images.map((url) => (
        <img key={url} src={url} alt="" className="max-w-xs max-h-64 rounded-xl object-contain border border-white/10 shadow-md" />
      ))}
      {media.videos.map((url) => (
        <video key={url} src={url} controls className="max-w-md max-h-64 rounded-xl border border-white/10 shadow-md" />
      ))}
      {media.audio.map((url) => (
        <audio key={url} src={url} controls className="w-full max-w-md" preload="none" />
      ))}
    </div>
  )
}
