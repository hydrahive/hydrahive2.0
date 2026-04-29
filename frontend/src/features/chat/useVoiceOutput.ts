import { useRef, useState } from "react"

export function useVoiceOutput() {
  const [speaking, setSpeaking] = useState(false)
  const uttRef = useRef<SpeechSynthesisUtterance | null>(null)

  function speak(text: string, lang = "de-DE") {
    window.speechSynthesis.cancel()
    const utt = new SpeechSynthesisUtterance(text)
    utt.lang = lang
    utt.rate = 1.0
    utt.onstart = () => setSpeaking(true)
    utt.onend = () => setSpeaking(false)
    utt.onerror = () => setSpeaking(false)
    uttRef.current = utt
    window.speechSynthesis.speak(utt)
  }

  function stop() {
    window.speechSynthesis.cancel()
    setSpeaking(false)
  }

  return { speaking, speak, stop }
}
