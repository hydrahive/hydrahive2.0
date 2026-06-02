// Hydra-Emoticons fürs Chat: Kürzel :hydra-NAME: → kleines Bild.
// Geteilt von EmoteText (Plain-Text-Bubbles) und remarkHydraEmotes (Markdown).

const EMOTE_NAMES = [
  "smile", "laughing", "wink", "cool", "silly", "wow",
  "heart", "love", "thumbsup", "idea", "rich", "rocket",
  "fire", "hmm", "sleepy", "angry", "cry",
] as const

export const HYDRA_EMOTES: Record<string, string> = Object.fromEntries(
  EMOTE_NAMES.filter((n) => n !== "love").map((n) => [n, `/illustrations/emoticons/hydra-${n}.png`])
)

// `love` ist ein Alias auf `heart` (geläufiges Kürzel, gleiche Grafik).
HYDRA_EMOTES.love = HYDRA_EMOTES.heart

export const EMOTE_RE = /:hydra-([a-z]+):/g

export type EmoteToken =
  | { type: "text"; value: string }
  | { type: "emote"; name: string; src: string }

/** Zerlegt Text in Text- und Emote-Stücke. Unbekannte Kürzel bleiben Literal-Text. */
export function tokenizeEmotes(text: string): EmoteToken[] {
  const out: EmoteToken[] = []
  let last = 0
  const re = new RegExp(EMOTE_RE.source, "g")
  let m: RegExpExecArray | null
  while ((m = re.exec(text)) !== null) {
    const src = HYDRA_EMOTES[m[1]]
    if (!src) continue // unbekannt → bleibt Teil des nächsten Text-Stücks
    if (m.index > last) out.push({ type: "text", value: text.slice(last, m.index) })
    out.push({ type: "emote", name: m[1], src })
    last = m.index + m[0].length
  }
  if (last < text.length) out.push({ type: "text", value: text.slice(last) })
  return out
}
