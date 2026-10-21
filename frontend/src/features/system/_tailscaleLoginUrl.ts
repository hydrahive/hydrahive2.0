/** Nur Links von tailscale.com öffnen (Anmeldung im Browser, docs/plans/mac-tailscale.md). */
export function isTailscaleLoginUrl(url: string | null | undefined): url is string {
  return typeof url === "string" && url.startsWith("https://login.tailscale.com/")
}
