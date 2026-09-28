import { useTranslation } from "react-i18next"
import { cn } from "@/shared/cn"
import { Field, TextInput } from "./_helpers"
import type { FormProps } from "./_helpers"

const ALL_DAYS = ["mo", "di", "mi", "do", "fr", "sa", "so"]
const DAY_LABEL: Record<string, string> = { mo: "Mo", di: "Di", mi: "Mi", do: "Do", fr: "Fr", sa: "Sa", so: "So" }

export function TimeWindowForm({ params, onChange }: FormProps) {
  const { t } = useTranslation("butler")
  return (
    <div className="flex flex-col gap-2">
      <Field label={t("labelFrom")}>
        <TextInput field="from" params={params} onChange={onChange} type="time" />
      </Field>
      <Field label={t("labelTo")}>
        <TextInput field="to" params={params} onChange={onChange} type="time" />
      </Field>
      <p className="text-[10px] text-white/25">{t("overnightSupported")}</p>
    </div>
  )
}

export function DayOfWeekForm({ params, onChange }: FormProps) {
  const { t } = useTranslation("butler")
  const days = (params.days as string[]) || ALL_DAYS
  return (
    <div>
      <label className="block text-xs text-white/50 mb-2">{t("labelDays")}</label>
      <div className="flex flex-wrap gap-1">
        {ALL_DAYS.map(day => {
          const active = days.includes(day)
          return (
            <button key={day} type="button"
              onClick={() => {
                const next = active ? days.filter(d => d !== day) : [...days, day]
                onChange({ ...params, days: next })
              }}
              className={cn(
                "w-8 py-1 rounded text-xs font-medium transition-colors",
                active ? "bg-blue-600 text-white" : "bg-zinc-900 text-white/35 hover:bg-white/10",
              )}
            >
              {DAY_LABEL[day]}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export function MessageContainsForm({ params, onChange }: FormProps) {
  const { t } = useTranslation("butler")
  return (
    <Field label={t("labelKeyword")}>
      <TextInput field="keyword" params={params} onChange={onChange}
        placeholder={t("placeholderKeywordExample")} />
    </Field>
  )
}

export function PayloadFieldContainsForm({ params, onChange }: FormProps) {
  const { t } = useTranslation("butler")
  return (
    <div className="flex flex-col gap-2">
      <Field label={t("labelFieldDotNotation")}>
        <TextInput field="field" params={params} onChange={onChange}
          placeholder={t("placeholderFieldExample")} />
      </Field>
      <Field label={t("labelValueContains")} hint={t("caseInsensitive")}>
        <TextInput field="value" params={params} onChange={onChange}
          placeholder={t("placeholderValueExample")} />
      </Field>
    </div>
  )
}

export function RegexMatchForm({ params, onChange }: FormProps) {
  const { t } = useTranslation("butler")
  return (
    <Field label={t("labelRegex")} hint={t("regexHint")}>
      <TextInput field="pattern" params={params} onChange={onChange}
        placeholder={"^/help\\b"} mono />
    </Field>
  )
}
