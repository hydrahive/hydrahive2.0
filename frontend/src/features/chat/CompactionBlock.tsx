import { useState } from "react"
import { Archive, ChevronDown, ChevronRight } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { Message } from "./types"

export function CompactionBlock({ message }: { message: Message }) {
  const { t, i18n } = useTranslation("chat")
  const [open, setOpen] = useState(false)
  const meta = message.metadata as { tokensBefore?: number; readFiles?: string[]; modifiedFiles?: string[] }
  const summary = typeof message.content === "string" ? message.content : JSON.stringify(message.content)
  const tokensSaved = meta.tokensBefore ?? 0
  const readCount = meta.readFiles?.length ?? 0
  const modifiedCount = meta.modifiedFiles?.length ?? 0
  const stats = tokensSaved > 0
    ? t("compaction_block.stats_with_tokens", {
        tokens: tokensSaved.toLocaleString(i18n.language),
        read: readCount,
        modified: modifiedCount,
      })
    : t("compaction_block.stats", { read: readCount, modified: modifiedCount })

  return (
    <div className="my-2 rounded-xl border border-amber-500/20 bg-amber-500/[5%]">
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-amber-500/[3%] transition-colors">
        {open ? <ChevronDown size={14} className="text-amber-300" /> : <ChevronRight size={14} className="text-amber-300" />}
        <Archive size={14} className="text-amber-300" />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-amber-200">{t("compaction_block.title")}</p>
          <p className="text-[10.5px] text-amber-400/70 mt-0.5">{stats}</p>
        </div>
      </button>
      {open && (
        <div className="px-4 pb-3 pt-1 space-y-2 border-t border-amber-500/10">
          {meta.readFiles && meta.readFiles.length > 0 && (
            <div>
              <p className="text-[10.5px] font-semibold uppercase tracking-wider text-amber-400/60 mb-1">{t("compaction_block.files_read")}</p>
              <pre className="text-[11px] text-amber-200/80 font-mono whitespace-pre-wrap">{meta.readFiles.join("\n")}</pre>
            </div>
          )}
          {meta.modifiedFiles && meta.modifiedFiles.length > 0 && (
            <div>
              <p className="text-[10.5px] font-semibold uppercase tracking-wider text-amber-400/60 mb-1">{t("compaction_block.files_modified")}</p>
              <pre className="text-[11px] text-amber-200/80 font-mono whitespace-pre-wrap">{meta.modifiedFiles.join("\n")}</pre>
            </div>
          )}
          <div>
            <p className="text-[10.5px] font-semibold uppercase tracking-wider text-amber-400/60 mb-1">{t("compaction_block.summary")}</p>
            <pre className="text-xs text-amber-100/90 whitespace-pre-wrap leading-relaxed">{summary}</pre>
          </div>
        </div>
      )}
    </div>
  )
}
