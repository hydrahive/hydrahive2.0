import { Lock } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Outlet, useLocation } from "react-router-dom"
import { moduleNavOwners } from "@/modules/index.generated"
import { pathAllowed } from "./navAccess"
import { useMyAccess } from "./useMyAccess"

// Ersetzt <Outlet /> im Layout: Seiten ohne Freigabe zeigen „Kein Zugriff“.
// Nur Oberfläche. Die Schnittstellen dahinter sperren ohnehin mit 403.
export function AccessOutlet() {
  const { pathname } = useLocation()
  const access = useMyAccess()
  if (pathAllowed(pathname, access, moduleNavOwners)) return <Outlet />
  return <NoAccess />
}

export function NoAccess() {
  const { t } = useTranslation("access")
  return (
    <div className="grid min-h-[60vh] place-items-center p-6">
      <div className="max-w-sm text-center">
        <Lock size={28} className="mx-auto mb-3 text-[#8d9ab0]" />
        <h2 className="text-lg font-bold text-[#e8eef8]">{t("no_access.title")}</h2>
        <p className="mt-2 text-sm text-[#8d9ab0]">{t("no_access.text")}</p>
      </div>
    </div>
  )
}
