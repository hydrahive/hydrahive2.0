/**
 * Statische Palette-Daten: Default-Params, i18n-Keys, Gruppen-Struktur
 * und Kurzbeschreibung pro Subtype für die Node-Vorschau.
 *
 * Bewusst nicht über die Backend-Registry — der Inspector rendert
 * subtype-spezifische Forms (jeder Subtype hat eigene Felder, kein
 * generisches ParamSchema). Dafür gilt: Hier steht nur, was der Server
 * auch ausführen kann. Das Backend lehnt unbekannte Subtypes beim Speichern
 * mit `butler_subtype_unknown` ab (Spec: butler-palette-webhook-cleanup.md).
 */
import {
  ArrowRight, Bot, Calendar, CalendarClock, Clock, EyeOff, Filter, GitBranch,
  GitPullRequest, Globe, Inbox, Mail, MessageCircle, MessageSquare, Regex,
  Webhook, Zap,
} from "lucide-react"

export function defaultParams(subtype: string): Record<string, unknown> {
  switch (subtype) {
    case "message_received":       return { channel: "all" }
    case "webhook_received":       return {}
    case "heartbeat_fired":        return { agent_id: "all", task_id: "" }
    case "cron_fired":             return { cron: "" }
    case "time_window":            return { from: "23:00", to: "08:00" }
    case "day_of_week":            return { days: ["mo","di","mi","do","fr","sa","so"] }
    case "message_contains":       return { keyword: "" }
    case "regex_match":            return { pattern: "" }
    case "payload_field_contains": return { field: "", value: "" }
    case "agent_reply":            return { agent_id: "" }
    case "agent_reply_guided":     return { agent_id: "", instruction: "" }
    case "reply_fixed":            return { text: "" }
    case "queue":                  return {}
    case "ignore":                 return {}
    case "forward":                return { agent_id: "" }
    case "http_post":              return { url: "", headers: {}, body: "{}" }
    case "send_email":             return { to: "", subject: "", body: "" }
    case "git_create_issue":       return { repo: "", title: "", body: "" }
    case "git_add_comment":        return { repo: "", issue_number: "", body: "" }
    case "discord_post":           return { channel_id: "", message: "" }
    default:                       return {}
  }
}

export const PALETTE_LABEL_KEY: Record<string, string> = {
  message_received:       "nodeMessageReceived",
  webhook_received:       "nodeWebhookReceived",
  heartbeat_fired:        "nodeHeartbeatTask",
  cron_fired:             "nodeCronFired",
  time_window:            "nodeTimeWindow",
  day_of_week:            "nodeDayOfWeek",
  message_contains:       "nodeMessageContains",
  regex_match:            "nodeRegexMatch",
  payload_field_contains: "nodePayloadFieldContains",
  agent_reply:            "nodeAgentReply",
  agent_reply_guided:     "nodeAgentReplyGuided",
  reply_fixed:            "nodeReplyFixed",
  queue:                  "nodeQueue",
  ignore:                 "nodeIgnore",
  forward:                "nodeForward",
  http_post:              "nodeHttpPost",
  send_email:             "nodeSendEmail",
  git_create_issue:       "nodeGitCreateIssue",
  git_add_comment:        "nodeGitAddComment",
  discord_post:           "nodeDiscordPost",
}

/** Aktionen, die der Server nur als Platzhalter kennt (Log-Eintrag, keine
 *  Wirkung). Badge in der Palette + Speichern blockiert, bis sie echt sind. */
export const UNWIRED_ACTIONS = new Set([
  "send_email",
  "git_create_issue",
  "git_add_comment",
  "discord_post",
])

export function isUnwired(subtype: string): boolean {
  return UNWIRED_ACTIONS.has(subtype)
}

export const PALETTE_STRUCTURE = [
  {
    groupKey: "groupTrigger",
    color: "green" as const,
    items: [
      { type: "triggerNode", subtype: "message_received",       icon: MessageCircle },
      { type: "triggerNode", subtype: "webhook_received",       icon: Webhook },
      { type: "triggerNode", subtype: "heartbeat_fired",        icon: Clock },
      { type: "triggerNode", subtype: "cron_fired",             icon: CalendarClock },
    ],
  },
  {
    groupKey: "groupCondition",
    color: "blue" as const,
    items: [
      { type: "conditionNode", subtype: "time_window",            icon: Clock },
      { type: "conditionNode", subtype: "day_of_week",            icon: Calendar },
      { type: "conditionNode", subtype: "message_contains",       icon: Filter },
      { type: "conditionNode", subtype: "regex_match",            icon: Regex },
      { type: "conditionNode", subtype: "payload_field_contains", icon: Filter },
    ],
  },
  {
    groupKey: "groupAction",
    color: "orange" as const,
    items: [
      { type: "actionNode", subtype: "agent_reply",         icon: Bot },
      { type: "actionNode", subtype: "agent_reply_guided",  icon: MessageCircle },
      { type: "actionNode", subtype: "reply_fixed",         icon: Zap },
      { type: "actionNode", subtype: "queue",               icon: Inbox },
      { type: "actionNode", subtype: "ignore",              icon: EyeOff },
      { type: "actionNode", subtype: "forward",             icon: ArrowRight },
      { type: "actionNode", subtype: "http_post",           icon: Globe },
      { type: "actionNode", subtype: "send_email",          icon: Mail },
      { type: "actionNode", subtype: "git_create_issue",    icon: GitPullRequest },
      { type: "actionNode", subtype: "git_add_comment",     icon: GitBranch },
      { type: "actionNode", subtype: "discord_post",        icon: MessageSquare },
    ],
  },
]
