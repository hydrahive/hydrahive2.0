import { SquarePen } from "lucide-react"
import { useTranslation } from "react-i18next"

const WARN_THRESHOLD = 20_000
const FRESH_BASELINE = 10_000

interface Props {
  inputTokens: number | null
  onNewChat: () => void
}

export function NewChatHint({ inputTokens, onNewChat }: Props) {
  const { t, i18n } = useTranslation("chat")
  if (!inputTokens || inputTokens < WARN_THRESHOLD) return null
  const savings = Math.max(0, inputTokens - FRESH_BASELINE)
  return (
    <div className="mx-4 mt-2 px-3 py-2 rounded-lg border border-amber-500/25 bg-amber-500/[5%] text-xs text-amber-300/90 flex items-center justify-between gap-3">
      <span>
        {t("session.context_large", {
          tokens: inputTokens.toLocaleString(i18n.language),
          savings: savings.toLocaleString(i18n.language),
        })}
      </span>
      <button
        onClick={onNewChat}
        className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-200 whitespace-nowrap transition-colors"
      >
        <SquarePen size={11} />
        {t("session.new_chat")}
      </button>
    </div>
  )
}
