export type FileKind = "text" | "image" | "video" | "audio" | "download"

const IMAGE = new Set(["png", "jpg", "jpeg", "gif", "webp", "svg", "avif", "bmp", "ico"])
const VIDEO = new Set(["mp4", "webm", "mov", "mkv", "m4v"])
const AUDIO = new Set(["mp3", "wav", "ogg", "flac", "m4a", "aac"])
// Bekannte Binär-Endungen → direkt Download, gar nicht erst als Text laden
const BINARY = new Set([
  "pdf", "zip", "tar", "gz", "bz2", "xz", "7z", "rar",
  "exe", "bin", "so", "dylib", "dll", "o", "a",
  "woff", "woff2", "ttf", "otf", "eot",
  "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt",
  "qcow2", "iso", "img", "db", "sqlite",
])

export function classifyFile(path: string): FileKind {
  const ext = path.split(".").pop()?.toLowerCase() ?? ""
  if (IMAGE.has(ext)) return "image"
  if (VIDEO.has(ext)) return "video"
  if (AUDIO.has(ext)) return "audio"
  if (BINARY.has(ext)) return "download"
  return "text"
}
