import { useTranslation } from "react-i18next"
import { AgentSelect, Field, Info, TextArea, TextInput } from "./_helpers"
import type { FormProps } from "./_helpers"

export function AgentReplyForm({ params, onChange, agents }: FormProps) {
  const { t } = useTranslation("butler")
  return (
    <Field label={t("labelAgent")}>
      <AgentSelect field="agent_id" params={params} onChange={onChange}
        agents={agents} placeholder={t("selectAgent")} />
    </Field>
  )
}

export function AgentReplyGuidedExtra({ params, onChange }: FormProps) {
  const { t } = useTranslation("butler")
  return (
    <Field label={t("labelInstruction")} hint={t("instructionPassedHint")}>
      <TextArea field="instruction" params={params} onChange={onChange} rows={3}
        placeholder={t("placeholderInstructionExample")} />
    </Field>
  )
}

export function ReplyFixedForm({ params, onChange }: FormProps) {
  const { t } = useTranslation("butler")
  return (
    <Field label={t("labelReplyText")} hint={t("replyDirectHint")}>
      <TextArea field="text" params={params} onChange={onChange} rows={4}
        placeholder={t("placeholderReplyExample")} />
    </Field>
  )
}

export function HttpPostForm({ params, onChange }: FormProps) {
  const { t } = useTranslation("butler")
  return (
    <div className="flex flex-col gap-2">
      <Field label={t("labelTargetUrl")}>
        <TextInput field="url" params={params} onChange={onChange}
          placeholder="https://example.com/webhook" />
      </Field>
      <Field label={t("labelBodyJson")}>
        <TextArea field="body_template" params={params} onChange={onChange} rows={4} mono
          placeholder={`{\n  "text": "{{event.message_text}}"\n}`} />
      </Field>
      <p className="text-[10px] text-white/25">
        {t("placeholderHint")} <code className="text-cyan-400">{"{{event.message_text}}"}</code>,{" "}
        <code className="text-cyan-400">{"{{event.extra.repo}}"}</code> etc.
      </p>
    </div>
  )
}

export function SendEmailForm({ params, onChange }: FormProps) {
  const { t } = useTranslation("butler")
  return (
    <div className="flex flex-col gap-2">
      <Field label={t("labelRecipient")}>
        <TextInput field="to" params={params} onChange={onChange}
          placeholder={t("placeholderRecipientExample")} />
      </Field>
      <Field label={t("labelSubject")}>
        <TextInput field="subject" params={params} onChange={onChange}
          placeholder={t("placeholderSubjectExample")} />
      </Field>
      <Field label={t("labelText")}>
        <TextArea field="body" params={params} onChange={onChange} rows={3}
          placeholder="{{event.message_text}}" />
      </Field>
      <p className="text-[10px] text-white/25">{t("smtpHint")}</p>
    </div>
  )
}

export function GitCreateIssueForm({ params, onChange }: FormProps) {
  const { t } = useTranslation("butler")
  return (
    <div className="flex flex-col gap-2">
      <Field label={t("labelRepo")}>
        <TextInput field="repo" params={params} onChange={onChange} placeholder="hydrahive/hydrahive" />
      </Field>
      <Field label={t("labelTitle")}>
        <TextInput field="title" params={params} onChange={onChange}
          placeholder="Bug: {{event.extra.commit_message}}" />
      </Field>
      <Field label={t("labelDescription")}>
        <TextArea field="body" params={params} onChange={onChange} rows={3}
          placeholder={t("placeholderTriggeredBy")} />
      </Field>
    </div>
  )
}

export function GitAddCommentForm({ params, onChange }: FormProps) {
  const { t } = useTranslation("butler")
  return (
    <div className="flex flex-col gap-2">
      <Field label={t("labelRepo")}>
        <TextInput field="repo" params={params} onChange={onChange} placeholder="hydrahive/hydrahive" />
      </Field>
      <Field label={t("labelIssueNumber")}>
        <TextInput field="issue_number" params={params} onChange={onChange}
          placeholder="42 oder {{event.extra.pr_number}}" />
      </Field>
      <Field label={t("labelComment")}>
        <TextArea field="body" params={params} onChange={onChange} rows={3}
          placeholder="Automatisch von Butler via {{event.channel}}" />
      </Field>
    </div>
  )
}

export function DiscordPostForm({ params, onChange }: FormProps) {
  const { t } = useTranslation("butler")
  return (
    <div className="flex flex-col gap-2">
      <Field label={t("labelChannelId")} hint={t("discordChannelIdHint")}>
        <TextInput field="channel_id" params={params} onChange={onChange}
          placeholder="1234567890123456789" mono />
      </Field>
      <Field label={t("labelMessage")}>
        <TextArea field="message" params={params} onChange={onChange} rows={3}
          placeholder="{{event.message_text}}" />
      </Field>
    </div>
  )
}

export function ContactKnownInfo() {
  const { t } = useTranslation("butler")
  return <Info>{t("contactKnownInfo")}</Info>
}

export function IgnoreInfo() {
  const { t } = useTranslation("butler")
  return <Info>{t("ignoreInfo")}</Info>
}

export function QueueInfo() {
  const { t } = useTranslation("butler")
  return <Info>{t("queueInfo")}</Info>
}
