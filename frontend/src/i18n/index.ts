import i18n from "i18next"
import LanguageDetector from "i18next-browser-languagedetector"
import { initReactI18next } from "react-i18next"

import deCommon from "./locales/de/common.json"
import deAuth from "./locales/de/auth.json"
import deNav from "./locales/de/nav.json"
import deChat from "./locales/de/chat.json"
import deAgents from "./locales/de/agents.json"
import deProjects from "./locales/de/projects.json"
import deLlm from "./locales/de/llm.json"
import deMcp from "./locales/de/mcp.json"
import deSystem from "./locales/de/system.json"
import deDashboard from "./locales/de/dashboard.json"
import deHelp from "./locales/de/help.json"
import deUsers from "./locales/de/users.json"
import deProfile from "./locales/de/profile.json"
import deErrors from "./locales/de/errors.json"
import dePlugins from "./locales/de/plugins.json"

import enCommon from "./locales/en/common.json"
import enAuth from "./locales/en/auth.json"
import enNav from "./locales/en/nav.json"
import enChat from "./locales/en/chat.json"
import enAgents from "./locales/en/agents.json"
import enProjects from "./locales/en/projects.json"
import enLlm from "./locales/en/llm.json"
import enMcp from "./locales/en/mcp.json"
import enSystem from "./locales/en/system.json"
import enDashboard from "./locales/en/dashboard.json"
import enHelp from "./locales/en/help.json"
import enUsers from "./locales/en/users.json"
import enProfile from "./locales/en/profile.json"
import enErrors from "./locales/en/errors.json"
import enPlugins from "./locales/en/plugins.json"

export const resources = {
  de: {
    common: deCommon, auth: deAuth, nav: deNav, chat: deChat,
    agents: deAgents, projects: deProjects, llm: deLlm, mcp: deMcp,
    system: deSystem, dashboard: deDashboard, help: deHelp, users: deUsers,
    profile: deProfile, errors: deErrors, plugins: dePlugins,
  },
  en: {
    common: enCommon, auth: enAuth, nav: enNav, chat: enChat,
    agents: enAgents, projects: enProjects, llm: enLlm, mcp: enMcp,
    system: enSystem, dashboard: enDashboard, help: enHelp, users: enUsers,
    profile: enProfile, errors: enErrors, plugins: enPlugins,
  },
} as const

export const SUPPORTED_LANGUAGES = [
  { code: "de", label: "Deutsch", flag: "🇩🇪" },
  { code: "en", label: "English", flag: "🇬🇧" },
] as const

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: "de",
    supportedLngs: SUPPORTED_LANGUAGES.map((l) => l.code),
    ns: ["common", "auth", "nav", "chat", "agents", "projects", "llm", "mcp", "system", "dashboard", "help", "users", "profile", "errors", "plugins"],
    defaultNS: "common",
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "hh2.lang",
    },
  })

export default i18n
