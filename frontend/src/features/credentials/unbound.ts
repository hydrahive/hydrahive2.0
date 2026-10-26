/** Zugänge ohne konkreten Host (url_pattern "*"): fetch_url setzt sie nie ein.
 *  Nur ausdrückliches `false` zählt – alte Einträge ohne Feld gelten als gebunden. */
export function countUnbound(creds: { host_bound?: boolean }[]): number {
  return creds.filter((c) => c.host_bound === false).length
}
