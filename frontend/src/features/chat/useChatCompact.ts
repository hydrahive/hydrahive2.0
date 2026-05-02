import { useState } from "react"
import { useTranslation } from "react-i18next"
import { chatApi } from "./api"

export function useChatCompact(
  activeId: string | null,
  reload: () => void,
  onRefresh: () => void,
) {
  const { t, i18n } = useTranslation("chat")
  const { t: tCommon } = useTranslation("common")
  const [compacting, setCompacting] = useState(false)
  const [compactNote, setCompactNote] = useState<string | null>(null)

  async function handleCompact() {
    if (!activeId) return
    setCompacting(true); setCompactNote(null)
    try {
      const r = await chatApi.compact(activeId)
      if (r.skipped) {
        const reason = r.reason_code
          ? t(`compact.reasons.${r.reason_code}`, r.reason_params ?? {})
          : "?"
        setCompactNote(t("compact.skipped", { reason }))
      } else {
        setCompactNote(
          r.tokens_before
            ? t("compact.result_with_tokens", {
                summarized: r.summarized_count,
                kept: r.kept_count,
                tokens: r.tokens_before.toLocaleString(i18n.language),
              })
            : t("compact.result", { summarized: r.summarized_count, kept: r.kept_count }),
        )
      }
      reload(); onRefresh()
    } catch (e) {
      setCompactNote(e instanceof Error ? e.message : tCommon("status.error"))
    } finally {
      setCompacting(false); setTimeout(() => setCompactNote(null), 5000)
    }
  }

  return { compacting, compactNote, handleCompact }
}
