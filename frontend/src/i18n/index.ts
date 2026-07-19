import i18n from "i18next"
import LanguageDetector from "i18next-browser-languagedetector"
import { initReactI18next } from "react-i18next"
import { moduleI18n } from "@/modules/index.generated"

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
import deCommunication from "./locales/de/communication.json"
import deButler from "./locales/de/butler.json"
import deSkills from "./locales/de/skills.json"
import deCredentials from "./locales/de/credentials.json"
import deBuddy from "./locales/de/buddy.json"
import deDatamining from "./locales/de/datamining.json"
import deMemory from "./locales/de/memory.json"
import deAnalytics from "./locales/de/analytics.json"
import deContainers from "./locales/de/containers.json"
import deExtensions from "./locales/de/extensions.json"
import deFederation from "./locales/de/federation.json"
import deStreaming from "./locales/de/streaming.json"
import deVms from "./locales/de/vms.json"
import deNodes from "./locales/de/nodes.json"
import deJobs from "./locales/de/jobs.json"
import deWorkspace from "./locales/de/workspace.json"
import deZahnfee from "./locales/de/zahnfee.json"
import deTeamchat from "./locales/de/teamchat.json"
import deModules from "./locales/de/modules.json"

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
import enCommunication from "./locales/en/communication.json"
import enButler from "./locales/en/butler.json"
import enSkills from "./locales/en/skills.json"
import enCredentials from "./locales/en/credentials.json"
import enBuddy from "./locales/en/buddy.json"
import enDatamining from "./locales/en/datamining.json"
import enMemory from "./locales/en/memory.json"
import enAnalytics from "./locales/en/analytics.json"
import enContainers from "./locales/en/containers.json"
import enExtensions from "./locales/en/extensions.json"
import enFederation from "./locales/en/federation.json"
import enStreaming from "./locales/en/streaming.json"
import enVms from "./locales/en/vms.json"
import enNodes from "./locales/en/nodes.json"
import enJobs from "./locales/en/jobs.json"
import enWorkspace from "./locales/en/workspace.json"
import enZahnfee from "./locales/en/zahnfee.json"
import enTeamchat from "./locales/en/teamchat.json"
import enModules from "./locales/en/modules.json"

const baseResources = {
  de: {
    common: deCommon, auth: deAuth, nav: deNav, chat: deChat,
    agents: deAgents, projects: deProjects, llm: deLlm, mcp: deMcp,
    system: deSystem, dashboard: deDashboard, help: deHelp, users: deUsers,
    profile: deProfile, errors: deErrors, plugins: dePlugins,
    communication: deCommunication, butler: deButler, skills: deSkills,
    credentials: deCredentials, buddy: deBuddy, datamining: deDatamining, memory: deMemory,
    analytics: deAnalytics, containers: deContainers, extensions: deExtensions,
    federation: deFederation,
    streaming: deStreaming, vms: deVms, nodes: deNodes, jobs: deJobs, workspace: deWorkspace, zahnfee: deZahnfee,
    teamchat: deTeamchat,
    modules: deModules,
  },
  en: {
    common: enCommon, auth: enAuth, nav: enNav, chat: enChat,
    agents: enAgents, projects: enProjects, llm: enLlm, mcp: enMcp,
    system: enSystem, dashboard: enDashboard, help: enHelp, users: enUsers,
    profile: enProfile, errors: enErrors, plugins: enPlugins,
    communication: enCommunication, butler: enButler, skills: enSkills,
    credentials: enCredentials, buddy: enBuddy, datamining: enDatamining, memory: enMemory,
    analytics: enAnalytics, containers: enContainers, extensions: enExtensions,
    federation: enFederation,
    streaming: enStreaming, vms: enVms, nodes: enNodes, jobs: enJobs, workspace: enWorkspace, zahnfee: enZahnfee,
    teamchat: enTeamchat,
    modules: enModules,
  },
}

// Merge module i18n bundles without clobbering existing namespaces
type LangResources = Record<string, Record<string, unknown>>
interface ModuleI18nBundle { de?: Record<string, unknown>; en?: Record<string, unknown> }
const mergedResources: { de: LangResources; en: LangResources } = {
  de: { ...baseResources.de } as LangResources,
  en: { ...baseResources.en } as LangResources,
}
for (const bundle of moduleI18n as ModuleI18nBundle[]) {
  if (bundle.de) Object.assign(mergedResources.de, bundle.de)
  if (bundle.en) Object.assign(mergedResources.en, bundle.en)
}

export const resources = mergedResources

export const SUPPORTED_LANGUAGES = [
  { code: "de", label: "Deutsch", flag: "🇩🇪" },
  { code: "en", label: "English", flag: "🇬🇧" },
] as const

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: mergedResources,
    fallbackLng: "de",
    supportedLngs: SUPPORTED_LANGUAGES.map((l) => l.code),
    ns: ["common", "auth", "nav", "chat", "agents", "projects", "llm", "mcp", "system", "dashboard", "help", "users", "profile", "errors", "plugins", "communication", "butler", "skills", "credentials", "buddy", "datamining", "memory", "analytics", "containers", "extensions", "federation", "streaming", "vms", "workspace", "zahnfee", "teamchat", "modules"],
    defaultNS: "common",
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "hh2.lang",
    },
  })

export default i18n
