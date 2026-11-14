import { parseTab } from "./ui"

/** Reiter des Fensters KI-Modelle. Steht in der Adresse (`tab=`), damit Hinweise direkt dorthin verlinken können. */
export const LLM_TABS = ["providers", "templates"] as const
export type LlmTab = (typeof LLM_TABS)[number]

export function parseLlmTab(wert: string | null): LlmTab {
  return parseTab(LLM_TABS, wert)
}

/** Vorgewähltes Template aus der Adresse (`template=`), nur gültige Kennungen. */
export function templateFromParams(params: URLSearchParams): string | null {
  const id = params.get("template")
  return id && /^[a-z0-9-]{1,64}$/.test(id) ? id : null
}
