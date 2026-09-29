import { useTranslation } from "react-i18next"
import { useMyAccess } from "./useMyAccess"

// Profil → „Meine Freigaben“ (nur lesend, docs/specs/access-groups.md §10).
export function MyAccessSection() {
  const { t } = useTranslation("access")
  const access = useMyAccess()
  if (!access) return null
  const caps = Object.entries(access.capabilities)
  return (
    <section className="space-y-2 rounded-[6px] border border-[#2a364b] bg-[#111827] p-4">
      <h3 className="text-sm font-bold text-[#e8eef8]">{t("me.title")}</h3>
      {access.admin && <p className="text-xs text-[#8d9ab0]">{t("me.admin")}</p>}
      {!access.admin && caps.length === 0 && <p className="text-xs text-[#8d9ab0]">{t("me.none")}</p>}
      {!access.admin && caps.length > 0 && (
        <ul className="space-y-1 text-xs text-[#e8eef8]">
          {caps.map(([cap, level]) => (
            <li key={cap}><code>{cap}</code> · {t(`grants.level_${level}`)}</li>
          ))}
        </ul>
      )}
      {access.groups.length > 0 && (
        <p className="text-xs text-[#8d9ab0]">{t("me.groups", { groups: access.groups.map((g) => g.name).join(", ") })}</p>
      )}
    </section>
  )
}
