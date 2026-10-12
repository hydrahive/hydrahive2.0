import { vaultApi } from "./api"
import { useVaultStore } from "./vaultStore"

/** Restzeit in ganzen Minuten, aufgerundet (entsperrt heißt remaining_seconds > 0 → mindestens 1). */
export function minutesLeft(seconds: number): number {
  return Math.ceil(seconds / 60)
}

/** Sofort sperren: Server macht alle Vault-Tokens ungültig; lokal vergessen wir ihn in jedem Fall. */
export async function lockNow(): Promise<void> {
  try { await vaultApi.lock() } catch { /* offline o. ä. – lokal trotzdem sperren */ }
  useVaultStore.getState().setToken(null)
}

/** Admin: Vault-PIN eines Nutzers entfernen (docs/specs/vault.md §4.4). */
export async function resetVaultPin(userId: string): Promise<void> {
  await vaultApi.adminReset(userId)
}
