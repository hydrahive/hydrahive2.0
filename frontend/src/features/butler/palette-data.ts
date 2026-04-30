/**
 * Statische Palette-Daten: Default-Params, i18n-Keys, Gruppen-Struktur
 * und Kurzbeschreibung pro Subtype für die Node-Vorschau.
 *
 * Bewusst nicht über die Backend-Registry (siehe /api/butler/registry) —
 * der alte octopos-Stil definiert die Palette client-seitig damit der
 * Inspector subtype-spezifische Forms rendern kann (jeder Subtype hat
 * eigene Felder, kein generisches ParamSchema).
 */
import {
  ArrowRight, Bot, Calendar, Clock, EyeOff, Filter, GitBranch, GitPullRequest,
  Globe, Inbox, Mail, MessageCircle, MessageSquare, Users, Webhook, Zap,
} from "lucide-react"

export function defaultParams(subtype: string): Record<string, unknown> {
  switch (subtype) {
    case "message_received":       return { channel: "all" }
    case "webhook_received":       return { hook_id: "" }
    case "heartbeat_fired":        return { agent_id: "all", task_id: "" }
    case "git_event_received":     return { git_event: "push", channel: "both", repo: "" }
    case "time_window":            return { from: "23:00", to: "08:00" }
    case "day_of_week":            return { days: ["mo","di","mi","do","fr","sa","so"] }
    case "contact_known":          return {}
    case "message_contains":       return { keyword: "" }
    case "payload_field_contains": return { field: "", value: "" }
    case "git_branch_is":          return { branch: "" }
    case "git_author_is":          return { author: "" }
    case "git_action_is":          return { action: "opened" }
    case "agent_reply":            return { agent_id: "" }
    case "agent_reply_guided":     return { agent_id: "", instruction: "" }
    case "reply_fixed":            return { text: "" }
    case "queue":                  return {}
    case "ignore":                 return {}
    case "forward":                return { agent_id: "" }
    case "http_post":              return { url: "", headers: {}, body_template: "{}" }
    case "send_email":             return { to: "", subject: "", body: "" }
    case "git_create_issue":       return { repo: "", title: "", body: "" }
    case "git_add_comment":        return { repo: "", issue_number: "", body: "" }
    case "discord_post":           return { channel_id: "", message: "" }
    case "discord_event_received": return { discord_event: "reaction_add", channel_id: "" }
    case "email_received":         return { folder: "INBOX", from_filter: "" }
    case "email_from_contains":    return { keyword: "" }
    case "email_subject_contains": return { keyword: "" }
    case "email_body_contains":    return { keyword: "" }
    case "discord_event_is":       return { discord_event: "reaction_add" }
    case "discord_emoji_is":       return { emoji: "" }
    default:                       return {}
  }
}

export const PALETTE_LABEL_KEY: Record<string, string> = {
  message_received:       "nodeMessageReceived",
  webhook_received:       "nodeWebhookReceived",
  heartbeat_fired:        "nodeHeartbeatTask",
  git_event_received:     "nodeGitEvent",
  discord_event_received: "nodeDiscordEvent",
  email_received:         "nodeEmailReceived",
  time_window:            "nodeTimeWindow",
  day_of_week:            "nodeDayOfWeek",
  contact_known:          "nodeContactKnown",
  message_contains:       "nodeMessageContains",
  payload_field_contains: "nodePayloadFieldContains",
  git_branch_is:          "nodeBranchIs",
  git_author_is:          "nodeAuthorIs",
  git_action_is:          "nodeGitActionIs",
  email_from_contains:    "nodeEmailFromContains",
  email_subject_contains: "nodeEmailSubjectContains",
  email_body_contains:    "nodeEmailBodyContains",
  discord_event_is:       "nodeDiscordEventIs",
  discord_emoji_is:       "nodeDiscordEmojiIs",
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

export const PALETTE_STRUCTURE = [
  {
    groupKey: "groupTrigger",
    color: "green" as const,
    items: [
      { type: "triggerNode", subtype: "message_received",       icon: MessageCircle },
      { type: "triggerNode", subtype: "webhook_received",       icon: Webhook },
      { type: "triggerNode", subtype: "heartbeat_fired",        icon: Clock },
      { type: "triggerNode", subtype: "git_event_received",     icon: GitBranch },
      { type: "triggerNode", subtype: "discord_event_received", icon: MessageSquare },
      { type: "triggerNode", subtype: "email_received",         icon: Mail },
    ],
  },
  {
    groupKey: "groupCondition",
    color: "blue" as const,
    items: [
      { type: "conditionNode", subtype: "time_window",            icon: Clock },
      { type: "conditionNode", subtype: "day_of_week",            icon: Calendar },
      { type: "conditionNode", subtype: "contact_known",          icon: Users },
      { type: "conditionNode", subtype: "message_contains",       icon: Filter },
      { type: "conditionNode", subtype: "payload_field_contains", icon: Filter },
      { type: "conditionNode", subtype: "git_branch_is",          icon: GitBranch },
      { type: "conditionNode", subtype: "git_author_is",          icon: Users },
      { type: "conditionNode", subtype: "git_action_is",          icon: Zap },
      { type: "conditionNode", subtype: "email_from_contains",    icon: Mail },
      { type: "conditionNode", subtype: "email_subject_contains", icon: Mail },
      { type: "conditionNode", subtype: "email_body_contains",    icon: Mail },
      { type: "conditionNode", subtype: "discord_event_is",       icon: MessageSquare },
      { type: "conditionNode", subtype: "discord_emoji_is",       icon: MessageSquare },
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
