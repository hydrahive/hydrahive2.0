/**
 * Erkennt Bild/Audio/Video-URLs in beliebigem Text und rendert sie als
 * Player. Genutzt in ToolResultCard (DevChat) und BuddyBubble.
 *
 * Bevorzugter Pfad: Backend liefert `tool_result.media` als strukturiertes
 * Feld (siehe runner/_media.py). Die Regex-basierte Extraktion ist nur noch
 * Fallback für freien Text (LLM-Antworten, ältere Sessions ohne media-Feld).
 */
import { useState } from "react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { EpubViewer } from "./EpubViewer"
import { ImageLightbox } from "./ImageLightbox"
import type { ToolMedia } from "./types"

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
// PDF/EPUB — absolute Pfade unter /tmp oder /var/lib/hydrahive2.
// Leerzeichen in Dateinamen erlaubt; Stopp an Newline, Pipe, Backtick, Quotes.
const ABS_PDF_RE = /(\/(?:tmp|var\/lib\/hydrahive2)\/[^\n\r|`"'\]{}]+\.pdf)/gi
const ABS_EPUB_RE = /(\/(?:tmp|var\/lib\/hydrahive2)\/[^\n\r|`"'\]{}]+\.epub)/gi

function toApiUrl(path: string): string {
  // <img>/<audio>/<video> können keinen Authorization-Header schicken — Token
  // als Query-Param mitgeben (Backend akzeptiert Bearer ODER ?token=).
  const token = useAuthStore.getState().token
  const tokenParam = token ? `&token=${encodeURIComponent(token)}` : ""
  return `/api/files?path=${encodeURIComponent(path)}${tokenParam}`
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
  pdfs: string[]
  epubs: string[]
}

export function extractMedia(text: string): ExtractedMedia {
  if (!text) return { images: [], audio: [], videos: [], pdfs: [], epubs: [] }
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
  const pdfs = matchAll(text, ABS_PDF_RE).map(toApiUrl)
  const epubs = matchAll(text, ABS_EPUB_RE).map(toApiUrl)
  return { images: dedupe(images), audio: dedupe(audio), videos: dedupe(videos), pdfs: dedupe(pdfs), epubs: dedupe(epubs) }
}

export function hasMedia(text: string): boolean {
  const m = extractMedia(text)
  return m.images.length + m.audio.length + m.videos.length + m.pdfs.length + m.epubs.length > 0
}

export function mediaFromBlocks(media: ToolMedia[] | undefined): ExtractedMedia {
  const empty: ExtractedMedia = { images: [], audio: [], videos: [], pdfs: [], epubs: [] }
  if (!media || media.length === 0) return empty
  const out: ExtractedMedia = { images: [], audio: [], videos: [], pdfs: [], epubs: [] }
  for (const m of media) {
    // url: direkter Link (z.B. von OpenRouter-API), path: lokale Datei via /api/files
    const resolved = m.url ?? (m.path ? toApiUrl(m.path) : null)
    if (!resolved) continue
    if (m.kind === "image") out.images.push(resolved)
    else if (m.kind === "audio") out.audio.push(resolved)
    else if (m.kind === "video") out.videos.push(resolved)
    else if (m.kind === "pdf") out.pdfs.push(resolved)
    else if (m.kind === "epub") out.epubs.push(resolved)
  }
  return out
}

function PdfViewer({ url }: { url: string }) {
  const [open, setOpen] = useState(false)
  const name = decodeURIComponent(url.split("path=")[1]?.split("&")[0] ?? "").split("/").pop() || "PDF"
  return (
    <div className="w-4/5">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-3 px-4 py-3 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 transition-colors w-full text-left"
      >
        <span className="text-2xl">📄</span>
        <span className="text-sm flex-1 truncate">{name}</span>
        <span className="text-xs text-white/40">{open ? "▲ schließen" : "▼ lesen"}</span>
      </button>
      {open && (
        <iframe
          src={url}
          className="w-full rounded-b-xl border border-t-0 border-white/10"
          style={{ height: "80vh" }}
          title={name}
        />
      )}
    </div>
  )
}

export function MediaPreview({ media }: { media: ExtractedMedia }) {
  if (media.images.length + media.audio.length + media.videos.length + media.pdfs.length + media.epubs.length === 0) return null
  return (
    <div className="space-y-2">
      {media.images.map((url) => (
        <ImageLightbox key={url} url={url} />
      ))}
      {media.videos.map((url) => (
        <video key={url} src={url} controls className="max-w-md max-h-64 rounded-xl border border-white/10 shadow-md" />
      ))}
      {media.audio.map((url) => (
        <audio key={url} src={url} controls className="w-full max-w-md" preload="none" />
      ))}
      {media.pdfs.map((url) => (
        <PdfViewer key={url} url={url} />
      ))}
      {media.epubs.map((url) => {
        const name = decodeURIComponent(url.split("path=")[1]?.split("&")[0] ?? "").split("/").pop() || "EPUB"
        return <EpubViewer key={url} url={url} name={name} />
      })}
    </div>
  )
}
