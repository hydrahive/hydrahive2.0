import { useState } from "react"
import { useTranslation } from "react-i18next"

type Landing = "buddy" | "dashboard"

const KEY = "hh_landing"

export function getLanding(): Landing {
  return (localStorage.getItem(KEY) as Landing) ?? "buddy"
}

export function LandingSwitcher() {
  const { t } = useTranslation("profile")
  const [current, setCurrent] = useState<Landing>(getLanding)

  function pick(v: Landing) {
    localStorage.setItem(KEY, v)
    setCurrent(v)
  }

  const options: { value: Landing; label: string }[] = [
    { value: "buddy", label: t("landing.buddy") },
    { value: "dashboard", label: t("landing.dashboard") },
  ]

  return (
    <div className="rounded-xl border border-white/[8%] bg-white/[2%] p-5 space-y-3">
      <div>
        <h2 className="text-sm font-semibold text-zinc-200">{t("landing.title")}</h2>
        <p className="text-xs text-zinc-500 mt-0.5">{t("landing.description")}</p>
      </div>
      <div className="flex gap-2">
        {options.map((o) => (
          <button
            key={o.value}
            onClick={() => pick(o.value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors border ${
              current === o.value
                ? "bg-violet-600/20 border-violet-500/50 text-violet-300"
                : "bg-white/[3%] border-white/[8%] text-zinc-400 hover:text-zinc-200"
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  )
}
