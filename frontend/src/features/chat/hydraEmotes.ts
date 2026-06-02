// Hydra-Emoticons fürs Chat: Kürzel :hydra-NAME: → kleines Bild.
// Geteilt von EmoteText (Plain-Text-Bubbles) und remarkHydraEmotes (Markdown).
//
// Die Namensliste wird AUTOMATISCH aus den PNG-Dateien generiert
// (scripts/gen-emotes.mjs → _emoteNames.generated.ts, läuft via npm prebuild).
// Neue Emotes brauchen keinen Code mehr — PNG reinlegen, fertig.
import { EMOTE_NAMES } from "./_emoteNames.generated"

export { EMOTE_NAMES }

export const HYDRA_EMOTES: Record<string, string> = Object.fromEntries(
  EMOTE_NAMES.map((n) => [n, `/illustrations/emoticons/hydra-${n}.png`])
)

// Freundliche Aliase auf gleichbedeutende Grafiken (geläufige Kürzel ohne eigene Datei).
const ALIASES: Record<string, string> = {
  heart: "love", laughing: "lol", rich: "money", silly: "lol",
}
for (const [alias, target] of Object.entries(ALIASES)) {
  if (HYDRA_EMOTES[target]) HYDRA_EMOTES[alias] = HYDRA_EMOTES[target]
}

export const EMOTE_RE = /:hydra-([a-z0-9-]+):/g

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
