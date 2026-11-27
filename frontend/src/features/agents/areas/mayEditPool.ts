/** Pool eines Agenten darf nur der Besitzer oder ein Admin ändern (Spec 4.4, Backend: PUT …/tool-pool → sonst 403). */
export function mayEditPool(owner: string | undefined, username: string | null | undefined, role: string | null | undefined): boolean {
  return role === "admin" || (!!username && !!owner && username === owner)
}
