import { useState, useRef, useEffect } from "react"
import { useLocation } from "react-router-dom"
import { Send } from "lucide-react"
import { buddyApi } from "@/features/buddy/api"
import { sendMessage } from "@/features/chat/api"

interface Message {
  role: "user" | "assistant"
  text: string
}

const SUGGESTIONS: Record<string, string[]> = {
  Condition: ["Erkläre meine Diagnosen", "Welche Diagnosen sind aktiv?", "Was bedeutet meine aktuelle Diagnose?"],
  Observation: ["Wie hat sich mein HbA1c entwickelt?", "Zeige meine letzten Laborwerte"],
  MedicationRequest: ["Welche Medikamente nehme ich?", "Wann wurden meine Medikamente verschrieben?"],
  default: [
    "Welche Diagnosen habe ich?",
    "Was sind meine aktuellen Medikamente?",
    "Wie haben sich meine Laborwerte entwickelt?",
    "Wann war mein letzter Arztbesuch?",
  ],
}

export function KiAssistentView() {
  const location = useLocation()
  const contextType = (location.state as { resourceType?: string } | null)?.resourceType
  const suggestions = SUGGESTIONS[contextType ?? "default"] ?? SUGGESTIONS.default

  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const send = async (text: string) => {
    if (!text.trim() || loading) return
    setMessages((prev) => [...prev, { role: "user", text }])
    setInput("")
    setLoading(true)

    try {
      const state = await buddyApi.state()
      const ac = new AbortController()
      abortRef.current = ac

      let reply = ""
      setMessages((prev) => [...prev, { role: "assistant", text: "" }])

      for await (const event of sendMessage(state.session_id, text, [], ac.signal)) {
        if (event.type === "text_delta") {
          reply += event.text
          setMessages((prev) => {
            const updated = [...prev]
            updated[updated.length - 1] = { role: "assistant", text: reply }
            return updated
          })
        } else if (event.type === "text") {
          reply = event.text
          setMessages((prev) => {
            const updated = [...prev]
            updated[updated.length - 1] = { role: "assistant", text: reply }
            return updated
          })
        } else if (event.type === "error") {
          setMessages((prev) => {
            const updated = [...prev]
            updated[updated.length - 1] = { role: "assistant", text: "Fehler bei der Antwort. Bitte erneut versuchen." }
            return updated
          })
          break
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") return
      setMessages((prev) => {
        const last = prev[prev.length - 1]
        if (last?.role === "assistant" && last.text === "") {
          const updated = [...prev]
          updated[updated.length - 1] = { role: "assistant", text: "Fehler bei der Antwort. Bitte erneut versuchen." }
          return updated
        }
        return [...prev, { role: "assistant", text: "Fehler bei der Antwort. Bitte erneut versuchen." }]
      })
    } finally {
      abortRef.current = null
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)]">
      <h2 className="text-base font-semibold text-zinc-100 mb-4">
        💬 KI-Assistent{contextType ? ` — ${contextType}` : ""}
      </h2>

      {messages.length === 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              className="px-3 py-1.5 text-xs rounded-lg bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-zinc-200 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="flex-1 overflow-y-auto space-y-3 pr-1">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm ${
              m.role === "user"
                ? "bg-indigo-600/20 text-indigo-200 border border-indigo-500/20"
                : "bg-zinc-800/60 text-zinc-200 border border-white/[6%]"
            }`}>
              {m.text}
            </div>
          </div>
        ))}
        {loading && messages[messages.length - 1]?.role !== "assistant" && (
          <div className="flex justify-start">
            <div className="bg-zinc-800/60 border border-white/[6%] rounded-xl px-4 py-2.5">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={(e) => { e.preventDefault(); send(input) }}
        className="mt-3 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Stelle eine Frage zu deiner Patientenakte…"
          className="flex-1 bg-zinc-900 border border-white/[8%] rounded-xl px-4 py-2.5 text-sm text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-indigo-500/40"
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-40 transition-colors"
        >
          <Send size={16} />
        </button>
      </form>
    </div>
  )
}
