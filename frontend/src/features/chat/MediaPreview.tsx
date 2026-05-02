/**
 * Erkennt Bild/Audio/Video-URLs in beliebigem Text und rendert sie als
 * Player. Genutzt in ToolResultCard (DevChat) und BuddyBubble.
 */

const IMG_RE = /(https?:\/\/[^\s)]+\.(?:png|jpe?g|gif|webp|svg|bmp|avif))(?:\?[^\s)]*)?/gi
const AUD_RE = /(https?:\/\/[^\s)]+\.(?:mp3|ogg|wav|m4a|opus|flac))(?:\?[^\s)]*)?/gi
const VID_RE = /(https?:\/\/[^\s)]+\.(?:mp4|webm|mov|m3u8))(?:\?[^\s)]*)?/gi
const FILE_IMG_RE = /(file:\/\/[^\s)]+\.(?:png|jpe?g|gif|webp|svg|bmp|avif))/gi
const FILE_AUD_RE = /(file:\/\/[^\s)]+\.(?:mp3|ogg|wav|m4a|opus|flac))/gi

export interface ExtractedMedia {
  images: string[]
  audio: string[]
  videos: string[]
}

export function extractMedia(text: string): ExtractedMedia {
  if (!text) return { images: [], audio: [], videos: [] }
  const dedupe = (xs: string[]) => Array.from(new Set(xs))
  return {
    images: dedupe([...(text.match(IMG_RE) || []), ...(text.match(FILE_IMG_RE) || [])]),
    audio:  dedupe([...(text.match(AUD_RE) || []), ...(text.match(FILE_AUD_RE) || [])]),
    videos: dedupe(text.match(VID_RE) || []),
  }
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
