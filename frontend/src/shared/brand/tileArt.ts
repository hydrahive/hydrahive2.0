/**
 * Eigene Hydra-Bildchen für Kacheln mit eigenem Ziel (Task 0dda5420, Stufe 2).
 * Ein Kopf von Tills Hydra mit einem Gegenstand, der zum Ziel passt (Motive: generated/hydra-design/kacheln/MOTIVE.md).
 * Schlüssel = Pfad der Kachel bzw. ein fester Name für Kacheln ohne eigenen Pfad.
 */
const K = "/kacheln"

export const TILE_ART: Record<string, string> = {
  "/system": `${K}/system.webp`, "/users": `${K}/user.webp`, "/modules": `${K}/module.webp`,
  "/extensions": `${K}/extensions.webp`, "/plugins": `${K}/plugins.webp`, "/credentials": `${K}/credentials.webp`,
  "/archive": `${K}/archiv.webp`, "/llm": `${K}/llm.webp`, "/mcp": `${K}/mcp.webp`, "/skills": `${K}/skills.webp`,
  "/vms": `${K}/vms.webp`, "/containers": `${K}/containers.webp`, "/nodes": `${K}/nodes.webp`, "/jobs": `${K}/jobs.webp`,
  "/scheduled-tasks": `${K}/automation.webp`, "/themes": `${K}/themes.webp`, "/federation": `${K}/federation.webp`,
  "/zahnfee-config": `${K}/zahnfee.webp`, "/system/settings": `${K}/system-settings.webp`, "/access": `${K}/freigaben.webp`,
  "/projects": `${K}/projekt.webp`, "/media": `${K}/media.webp`, "/vault": `${K}/vault.webp`, "/admin": `${K}/admin.webp`,
  "/scratchpad": `${K}/scratchpad.webp`, "/minigames": `${K}/spiele.webp`, "/boardgames": `${K}/boardgames.webp`,
  "buddy:today": `${K}/heute.webp`, "buddy:remember": `${K}/idee.webp`, "buddy:project": `${K}/projekt.webp`,
  gitea: `${K}/gitea.webp`, backup: `${K}/backup.webp`,
}

export function tileArt(target: string): string | null {
  return Object.hasOwn(TILE_ART, target) ? TILE_ART[target] : null
}
