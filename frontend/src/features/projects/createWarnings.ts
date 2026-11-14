/** Warnungen und Fehler beim Projekt-Anlegen, die auf die Template-Seite verweisen (Kern: projects/_model_check). */

export interface CreateWarning { code: string; template: string; model: string; link: string }
export interface TemplateHint { template: string; model: string; link: string }

const KNOWN = new Set(["template_fallback_unavailable", "template_not_configured"])
const TEMPLATE_LINK = /^\/admin\?section=llm&tab=templates(&template=[a-z0-9-]{1,64})?$/

export function createWarningKey(code: string): string {
  return `create_warning.${KNOWN.has(code) ? code : "general"}`
}

/** Nur eigene, relative Links auf die Template-Seite – nie fremde Adressen aus der Antwort übernehmen. */
export function isTemplateLink(link: unknown): link is string {
  return typeof link === "string" && TEMPLATE_LINK.test(link)
}

/** Template-Hinweis aus einem API-Fehler „Hauptmodell nicht verfügbar“, sonst null. */
export function templateHint(err: unknown): TemplateHint | null {
  if (!err || typeof err !== "object") return null
  const { code, params } = err as { code?: string; params?: Record<string, unknown> }
  if (code !== "template_primary_unavailable" || !params || !isTemplateLink(params.link)) return null
  return { template: String(params.template ?? ""), model: String(params.model ?? ""), link: params.link }
}
