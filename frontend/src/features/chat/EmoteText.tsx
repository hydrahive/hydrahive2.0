import { tokenizeEmotes } from "./hydraEmotes"

/** Rendert Plain-Text mit inline Hydra-Emoticons (für Bubbles ohne Markdown). */
export function EmoteText({ text }: { text: string }) {
  const tokens = tokenizeEmotes(text)
  return (
    <>
      {tokens.map((tok, i) =>
        tok.type === "text" ? (
          <span key={i}>{tok.value}</span>
        ) : (
          <img key={i} src={tok.src} alt={`:hydra-${tok.name}:`} title={tok.name} className="hydra-emote" />
        )
      )}
    </>
  )
}
