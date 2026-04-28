import { useTranslation } from "react-i18next"
import { Languages } from "lucide-react"
import { SUPPORTED_LANGUAGES } from "./index"

export function LanguageSwitcher({ compact = false }: { compact?: boolean }) {
  const { i18n } = useTranslation()
  const current = SUPPORTED_LANGUAGES.find((l) => l.code === i18n.language.split("-")[0])
    ?? SUPPORTED_LANGUAGES[0]

  function setLang(code: string) {
    i18n.changeLanguage(code)
  }

  if (compact) {
    return (
      <div className="flex items-center gap-1">
        {SUPPORTED_LANGUAGES.map((l) => (
          <button
            key={l.code}
            onClick={() => setLang(l.code)}
            title={l.label}
            className={`px-1.5 py-0.5 rounded text-xs transition-colors ${
              current.code === l.code
                ? "bg-violet-500/20 text-violet-200"
                : "text-zinc-500 hover:text-zinc-300 hover:bg-white/5"
            }`}
          >
            {l.flag}
          </button>
        ))}
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[3%] border border-white/[6%]">
      <Languages size={13} className="text-zinc-500 flex-shrink-0" />
      <div className="flex items-center gap-1 flex-1">
        {SUPPORTED_LANGUAGES.map((l) => (
          <button
            key={l.code}
            onClick={() => setLang(l.code)}
            className={`flex-1 px-2 py-1 rounded text-xs font-medium transition-all ${
              current.code === l.code
                ? "bg-gradient-to-r from-indigo-600/30 to-violet-600/20 text-zinc-100"
                : "text-zinc-500 hover:text-zinc-300 hover:bg-white/5"
            }`}
          >
            {l.flag} {l.label}
          </button>
        ))}
      </div>
    </div>
  )
}
