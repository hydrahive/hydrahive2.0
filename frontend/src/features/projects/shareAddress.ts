/** Adresse der Projekt-Freigabe (docs/plans/mac-file-sharing.md §2.4).
 * Linux (Samba): Windows-Schreibweise zuerst. Mac (macOS-Dateifreigabe): smb:// zuerst – so verbindet der Finder
 * („Gehe zu → Mit Server verbinden“). Die jeweils andere Schreibweise steht darunter. */
export type SharePlatform = "linux" | "mac"

export function shareAddresses(platform: SharePlatform | undefined, host: string, share: string) {
  const win = `\\\\${host}\\${share}`
  const smb = `smb://${host}/${share}`
  return platform === "mac" ? { primary: smb, secondary: win } : { primary: win, secondary: smb }
}
