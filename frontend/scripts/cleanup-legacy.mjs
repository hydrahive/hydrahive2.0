// Räumt beim Build Altlasten weg, die auf bestehenden Installationen liegen, aber
// nie im Repo waren (generiert + .gitignore) und darum ein Update nicht entfernt.
//
// src/themes/: generiertes Register des Layout-Theme-Systems (bis #653) und per
// Hub installierte Theme-Pakete. Das System ist entfernt (Task 3c82a8d5); die
// liegengebliebene index.generated.ts verweist auf @/shared/themes/types und
// bricht sonst `tsc -b` beim Update ab.
import { existsSync, rmSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const root = join(dirname(fileURLToPath(import.meta.url)), "..")
const LEGACY = ["src/themes"]

for (const rel of LEGACY) {
  const p = join(root, rel)
  if (existsSync(p)) {
    rmSync(p, { recursive: true, force: true })
    console.log(`cleanup-legacy: ${rel} entfernt (Altlast)`)
  }
}
