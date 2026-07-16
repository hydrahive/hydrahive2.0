import { useEffect, useId, useState } from "react"
import { Loader2, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Markdown } from "@/features/chat/Markdown"
import { type HelpTopic, loadHelp } from "./help/loader"

interface Props {
  topic: HelpTopic
  open: boolean
  onClose: () => void
}

export function HelpDrawer({ topic, open, onClose }: Props) {
  const { t, i18n } = useTranslation("help")
  const titleId = useId()
  const [content, setContent] = useState("")
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open) return
    let active = true
    const initial = window.setTimeout(() => {
      setLoading(true)
      loadHelp(topic, i18n.language)
        .then((nextContent) => { if (active) setContent(nextContent) })
        .finally(() => { if (active) setLoading(false) })
    }, 0)
    return () => { active = false; window.clearTimeout(initial) }
  }, [open, topic, i18n.language])

  return (
    <>
      <div
        className={`fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm transition-opacity ${open ? "opacity-100" : "pointer-events-none opacity-0"}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        className={`fixed bottom-0 right-0 top-0 z-[90] flex w-full max-w-2xl flex-col border-l border-[#46617f] bg-[#0e1420] shadow-2xl transition-transform duration-200 ${open ? "translate-x-0" : "translate-x-full"}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-hidden={!open}
      >
        <header className="flex items-center justify-between border-b border-[#2a364b] bg-[#131b2a] px-5 py-4">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#69d7ff]">Hilfe</p>
            <h2 id={titleId} className="text-lg font-black text-[#e8eef8]">{t("drawer.title")}</h2>
          </div>
          <button type="button" onClick={onClose} className="rounded-[4px] p-2 text-[#8d9ab0] hover:bg-[#172133] hover:text-[#e8eef8]" title={t("drawer.close")} aria-label={t("drawer.close")}>
            <X size={16} />
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4 text-[#d4deeb]">
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-[#8d9ab0]">
              <Loader2 size={14} className="animate-spin" /> Lädt…
            </div>
          ) : <Markdown text={content} />}
        </div>
      </aside>
    </>
  )
}
