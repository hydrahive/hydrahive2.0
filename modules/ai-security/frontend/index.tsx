import { AISecurityPage } from "./AISecurityPage"

export const routes = [{ path: "/ai-security", element: <AISecurityPage /> }]
export const nav = [
  { path: "/ai-security", icon: "ShieldCheck", labelKey: "aiSecurity", group: "infrastructure", roles: ["admin"] as ("admin" | "user")[] },
]
export const i18n = {
  de: { aiSecurity: "AI-Sicherheit" },
  en: { aiSecurity: "AI Security" },
}
