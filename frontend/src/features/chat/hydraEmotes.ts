// Hydra-Emoticons fürs Chat: Kürzel :hydra-NAME: → kleines Bild.
// Geteilt von EmoteText (Plain-Text-Bubbles) und remarkHydraEmotes (Markdown).

// Kanonische Emotes (= Dateien hydra-NAME.png). Reihenfolge = Picker-Reihenfolge.
export const EMOTE_NAMES = [
  "smile", "grin", "lol", "tears", "rofl",
  "wink", "kiss", "smirk", "cool", "sunglasses",
  "love", "plead", "hmm", "monocle", "wow",
  "hushed", "scared", "explode", "angry", "unamused",
  "facepalm", "cry", "nerd", "money", "fire",
  "idea", "party", "thumbsup", "sleepy", "neutral",
  "shush", "zipper", "devil", "angel", "sick",
  "cowboy", "alien", "drool", "rocket",
  // Charakter-Hydras
  "pirate", "ninja", "wizard", "king", "chef",
  "hacker", "detective", "builder", "coffee", "borg",
  "brainfull", "doublefacepalm",
  // Symbole & Objekte (datengetrieben — meistgenutzte Emojis der Agenten)
  "checkmark", "cross", "warning", "chart", "vulcan",
  "muscle", "lobster", "trophy", "sparkle", "lightning",
  "shield", "search", "bug", "brain", "bulb",
  "robot", "refresh", "handshake", "wave", "eyes",
  "books", "graduation", "lab", "palette", "hammer",
  "wrench", "plug", "globe", "moon", "bee",
  "clapper", "theater",
] as const

export const HYDRA_EMOTES: Record<string, string> = Object.fromEntries(
  EMOTE_NAMES.map((n) => [n, `/illustrations/emoticons/hydra-${n}.png`])
)

// Freundliche Aliase auf die gleiche Grafik (geläufige Kürzel; heart hat keine
// eigene Datei → nutzt love).
const ALIASES: Record<string, string> = {
  heart: "love", laughing: "lol", rich: "money", silly: "lol",
}
for (const [alias, target] of Object.entries(ALIASES)) {
  HYDRA_EMOTES[alias] = HYDRA_EMOTES[target]
}

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
