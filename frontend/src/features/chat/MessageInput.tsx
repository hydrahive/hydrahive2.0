import { Send, Square } from "lucide-react"
import { useRef, useState } from "react"

interface Props {
  onSend: (text: string) => void
  onCancel?: () => void
  busy: boolean
  disabled?: boolean
}

export function MessageInput({ onSend, onCancel, busy, disabled }: Props) {
  const [text, setText] = useState("")
  const ref = useRef<HTMLTextAreaElement>(null)

  function submit() {
    const trimmed = text.trim()
    if (!trimmed || busy) return
    onSend(trimmed)
    setText("")
    if (ref.current) ref.current.style.height = "auto"
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  function handleInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setText(e.target.value)
    const el = e.target
    el.style.height = "auto"
    el.style.height = Math.min(el.scrollHeight, 200) + "px"
  }

  return (
    <div className="border-t border-white/[6%] p-4">
      <div className="flex items-end gap-2 rounded-2xl border border-white/[8%] bg-white/[3%] px-3 py-2 focus-within:border-violet-500/40 focus-within:bg-white/[5%] transition-all">
        <textarea
          ref={ref}
          value={text}
          onChange={handleInput}
          onKeyDown={handleKey}
          placeholder={disabled ? "Wähle erst eine Session…" : "Nachricht schreiben…"}
          disabled={disabled}
          rows={1}
          className="flex-1 bg-transparent text-sm text-zinc-200 placeholder:text-zinc-600 resize-none focus:outline-none py-1.5 disabled:opacity-50"
        />
        {busy && onCancel ? (
          <button
            onClick={onCancel}
            type="button"
            title="Stop — Antwort abbrechen"
            className="flex-shrink-0 p-2 rounded-xl bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/30 text-rose-300 transition-all"
          >
            <Square size={14} fill="currentColor" />
          </button>
        ) : (
          <button
            onClick={submit}
            disabled={busy || !text.trim() || disabled}
            className="flex-shrink-0 p-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-md shadow-violet-900/20"
          >
            <Send size={15} />
          </button>
        )}
      </div>
      <p className="text-[10px] text-zinc-600 mt-1.5 px-1">
        Enter zum Senden · Shift+Enter für neue Zeile
      </p>
    </div>
  )
}
