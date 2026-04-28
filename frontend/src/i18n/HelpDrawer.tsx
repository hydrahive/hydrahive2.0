import { useEffect, useState } from "react"
import { X, Loader2 } from "lucide-react"
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
  const [content, setContent] = useState<string>("")
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    loadHelp(topic, i18n.language)
      .then(setContent)
      .finally(() => setLoading(false))
  }, [open, topic, i18n.language])

  return (
    <>
      <div
        className={`fixed inset-0 bg-black/40 backdrop-blur-sm z-40 transition-opacity ${
          open ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
        onClick={onClose}
      />
      <aside
        className={`fixed top-0 right-0 bottom-0 w-full max-w-2xl bg-zinc-950 border-l border-white/[8%] shadow-2xl shadow-black/50 z-50 flex flex-col transition-transform duration-200 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[6%]">
          <h2 className="text-lg font-bold text-white">{t("drawer.title")}</h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-200 hover:bg-white/5 transition-colors"
            title={t("drawer.close")}
          >
            <X size={16} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {loading && (
            <div className="flex items-center gap-2 text-sm text-zinc-500">
              <Loader2 size={14} className="animate-spin" /> Lädt…
            </div>
          )}
          {!loading && <Markdown text={content} />}
        </div>
      </aside>
    </>
  )
}
