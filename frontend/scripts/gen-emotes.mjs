// Generiert die Emote-Namensliste aus den vorhandenen PNG-Dateien.
// Lauf: `node scripts/gen-emotes.mjs` (oder automatisch via npm prebuild).
// Neuer Emote = PNG reinlegen, Skript laufen lassen, fertig — keine Handliste.
import { readdirSync, writeFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

const here = dirname(fileURLToPath(import.meta.url))
const emoteDir = join(here, "..", "public", "illustrations", "emoticons")
const outFile = join(here, "..", "src", "features", "chat", "_emoteNames.generated.ts")

const names = readdirSync(emoteDir)
  .filter((f) => /^hydra-[a-z0-9-]+\.png$/.test(f) && f !== "hydra-wow2.png")
  .map((f) => f.slice("hydra-".length, -".png".length))
  .sort()

const body =
  "// AUTO-GENERIERT von scripts/gen-emotes.mjs — nicht von Hand editieren.\n" +
  "// Quelle: public/illustrations/emoticons/hydra-*.png\n" +
  `export const EMOTE_NAMES: readonly string[] = ${JSON.stringify(names, null, 2)}\n`

writeFileSync(outFile, body)
console.log(`gen-emotes: ${names.length} Emotes → src/features/chat/_emoteNames.generated.ts`)
