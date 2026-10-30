import { useTranslation } from "react-i18next"
import { MOBILE_TABS, type MobileTab } from "./mobileTabs"

interface Props {
  active: MobileTab
  onChange: (tab: MobileTab) => void
}

/** Reiterleiste Projekt · Chat · Dateien & Tasks, nur unter 1280 px sichtbar. */
export function ProjectMobileTabs({ active, onChange }: Props) {
  const { t } = useTranslation("projects")
  return (
    <div
      role="tablist"
      aria-label={t("cockpit_tabs.label")}
      className="mx-[10px] mt-[10px] grid shrink-0 grid-cols-3 gap-1 rounded-[4px] border border-s-rand bg-s-box p-1 xl:hidden"
    >
      {MOBILE_TABS.map((tab) => {
        const selected = tab === active
        return (
          <button
            key={tab}
            type="button"
            role="tab"
            id={`project-tab-${tab}`}
            aria-selected={selected}
            aria-controls={`project-pane-${tab}`}
            onClick={() => onChange(tab)}
            className={`min-w-0 truncate rounded-[3px] px-1 py-2 text-xs font-bold sm:px-2 sm:text-sm transition-colors ${
              selected ? "bg-[#1c2940] text-[#69d7ff]" : "text-[#9aa7bc] hover:bg-white/5 hover:text-[#e8eef8]"
            }`}
          >
            {t(`cockpit_tabs.${tab}`)}
          </button>
        )
      })}
    </div>
  )
}
