/**
 * Kurzbeschreibung pro Subtype für die Node-Vorschau auf dem Canvas.
 * Wird vom NodeRenderer aufgerufen — `t` ist der i18n-Translator.
 */
export function paramSummary(
  subtype: string,
  params: Record<string, unknown>,
  t: (key: string) => string,
): string {
  switch (subtype) {
    case "message_received": {
      const ch = (params.channel as string) || "all"
      return ch === "all" ? t("allChannels") : ch.charAt(0).toUpperCase() + ch.slice(1)
    }
    case "webhook_received":
      return t("webhookAnyHint")
    case "heartbeat_fired": {
      const agent = (params.agent_id as string) || "all"
      const task  = (params.task_id as string) || ""
      return agent === "all"
        ? (task ? `${t("allAgents")} · ${task}` : t("allAgents"))
        : (task ? `${agent} · ${task}` : agent)
    }
    case "cron_fired":
      return (params.cron as string) || t("cronMissing")
    case "payload_field_contains":
      return params.field ? `${params.field} ≈ "${params.value}"` : "—"
    case "time_window":
      return `${params.from ?? "?"}–${params.to ?? "?"}`
    case "day_of_week": {
      const days = (params.days as string[]) ?? []
      return days.map((d) => d.charAt(0).toUpperCase() + d.slice(1)).join(" ")
    }
    case "message_contains":
      return params.keyword ? `"${params.keyword}"` : "—"
    case "regex_match":
      return (params.pattern as string) ? `/${params.pattern}/` : "—"
    case "agent_reply":
    case "forward":
      return (params.agent_id as string) || "—"
    case "agent_reply_guided":
      return (params.instruction as string)?.slice(0, 30) || "—"
    case "reply_fixed":
      return (params.text as string)?.slice(0, 30) || "—"
    case "http_post":
      return (params.url as string)?.slice(0, 35) || t("urlMissing")
    case "send_email":
      return (params.to as string) || t("toMissing")
    case "git_create_issue":
      return (params.repo as string)
        ? `${params.repo}: ${(params.title as string)?.slice(0, 20) || ""}`
        : t("repoMissing")
    case "git_add_comment":
      return (params.repo as string)
        ? `${params.repo} #${params.issue_number || "?"}`
        : t("repoMissing")
    case "discord_post":
      return (params.channel_id as string) ? `#${params.channel_id}` : t("channelMissing")
    default:
      return ""
  }
}
