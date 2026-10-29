/**
 * Alte Adressen des Einstellungs-Hubs für Admin-Dinge (/settings/<gruppe>).
 * Diese Einstellungen haben ihr einziges Zuhause im Admin-Cockpit
 * (docs/plans/meine-einstellungen.md); Lesezeichen und alte Links landen dort.
 */
export const ADMIN_GROUP_TARGET: Record<string, string> = {
  modules: "/admin?section=modules",
  plugins: "/admin?section=plugins",
  extensions: "/admin?section=extensions",
  mcp: "/admin?section=mcp",
  llm: "/admin?section=llm",
  federation: "/admin?section=federation",
  connections: "/admin?section=system",
  system: "/admin?section=system",
  settings_values: "/admin?section=system-settings",
  users: "/admin?section=users",
  zahnfee: "/admin?section=zahnfee",
}

/** Ziel im Admin-Cockpit oder null, wenn die Gruppe in „Meine Einstellungen“ bleibt. */
export function legacyTarget(groupId: string | undefined): string | null {
  return groupId && Object.hasOwn(ADMIN_GROUP_TARGET, groupId) ? ADMIN_GROUP_TARGET[groupId] : null
}
