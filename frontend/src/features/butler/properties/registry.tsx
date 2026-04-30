/**
 * Subtype → Form-Component-Registry für den Butler-PropertiesPanel.
 *
 * Jede Form bekommt { params, onChange, agents? } und rendert das spezifische
 * Subform. Subtypes ohne Eintrag in der Map zeigen kein Form-Body — nur Header
 * + Delete-Button.
 */
import type { ComponentType } from "react"
import {
  AgentReplyForm, AgentReplyGuidedExtra, ContactKnownInfo, DiscordPostForm,
  GitAddCommentForm, GitCreateIssueForm, HttpPostForm, IgnoreInfo,
  QueueInfo, ReplyFixedForm, SendEmailForm,
} from "./_actions"
import {
  DiscordEmojiIsForm, DiscordEventIsForm, EmailContainsForm,
  GitActionIsForm, GitAuthorIsForm, GitBranchIsForm,
  MessageContainsForm, PayloadFieldContainsForm, TimeWindowForm, DayOfWeekForm,
} from "./_conditions"
import type { FormProps } from "./_helpers"
import {
  DiscordEventReceivedForm, EmailReceivedForm, GitEventForm,
  HeartbeatForm, MessageReceivedForm,
} from "./_triggers"
import { WebhookTriggerForm } from "./_webhook"

type FormComponent = ComponentType<FormProps & { subtype?: string }>

export const FORMS: Record<string, FormComponent> = {
  // Triggers
  webhook_received: WebhookTriggerForm,
  git_event_received: GitEventForm,
  heartbeat_fired: HeartbeatForm,
  message_received: MessageReceivedForm,
  discord_event_received: DiscordEventReceivedForm,
  email_received: EmailReceivedForm,
  // Conditions
  time_window: TimeWindowForm,
  day_of_week: DayOfWeekForm,
  message_contains: MessageContainsForm,
  payload_field_contains: PayloadFieldContainsForm,
  git_branch_is: GitBranchIsForm,
  git_author_is: GitAuthorIsForm,
  git_action_is: GitActionIsForm,
  email_from_contains: EmailContainsForm,
  email_subject_contains: EmailContainsForm,
  email_body_contains: EmailContainsForm,
  discord_event_is: DiscordEventIsForm,
  discord_emoji_is: DiscordEmojiIsForm,
  // Actions
  agent_reply: AgentReplyForm,
  forward: AgentReplyForm,
  agent_reply_guided: AgentReplyForm,
  reply_fixed: ReplyFixedForm,
  http_post: HttpPostForm,
  send_email: SendEmailForm,
  git_create_issue: GitCreateIssueForm,
  git_add_comment: GitAddCommentForm,
  discord_post: DiscordPostForm,
  contact_known: ContactKnownInfo,
  ignore: IgnoreInfo,
  queue: QueueInfo,
}

// Subtypes die einen extra Form-Block ANGEBOTEN bekommen ZUSÄTZLICH zur Haupt-Form
// (z.B. agent_reply_guided: AgentSelect + Instruction-Textarea).
export const EXTRA_FORMS: Record<string, FormComponent> = {
  agent_reply_guided: AgentReplyGuidedExtra,
}
