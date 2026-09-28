/**
 * Subtype → Form-Component-Registry für den Butler-PropertiesPanel.
 *
 * Jede Form bekommt { params, onChange, agents? } und rendert das spezifische
 * Subform. Subtypes ohne Eintrag in der Map zeigen kein Form-Body — nur Header
 * + Delete-Button.
 */
import type { ComponentType } from "react"
import {
  AgentReplyForm, AgentReplyGuidedExtra, DiscordPostForm,
  GitAddCommentForm, GitCreateIssueForm, HttpPostForm, IgnoreInfo,
  QueueInfo, ReplyFixedForm, SendEmailForm,
} from "./_actions"
import {
  DayOfWeekForm, MessageContainsForm, PayloadFieldContainsForm,
  RegexMatchForm, TimeWindowForm,
} from "./_conditions"
import type { FormProps } from "./_helpers"
import { CronForm, HeartbeatForm, MessageReceivedForm } from "./_triggers"
import { WebhookTriggerForm } from "./_webhook"

type FormComponent = ComponentType<FormProps & { subtype?: string }>

export const FORMS: Record<string, FormComponent> = {
  // Triggers
  webhook_received: WebhookTriggerForm,
  heartbeat_fired: HeartbeatForm,
  cron_fired: CronForm,
  message_received: MessageReceivedForm,
  // Conditions
  time_window: TimeWindowForm,
  day_of_week: DayOfWeekForm,
  message_contains: MessageContainsForm,
  regex_match: RegexMatchForm,
  payload_field_contains: PayloadFieldContainsForm,
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
  ignore: IgnoreInfo,
  queue: QueueInfo,
}

// Subtypes die einen extra Form-Block ANGEBOTEN bekommen ZUSÄTZLICH zur Haupt-Form
// (z.B. agent_reply_guided: AgentSelect + Instruction-Textarea).
export const EXTRA_FORMS: Record<string, FormComponent> = {
  agent_reply_guided: AgentReplyGuidedExtra,
}
