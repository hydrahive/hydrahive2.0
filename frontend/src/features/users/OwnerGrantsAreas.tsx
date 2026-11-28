import { useTranslation } from "react-i18next"
import { PoolAreasEditor } from "@/features/agents/areas/PoolAreasEditor"

/** Besitzer-Freigabe eines Nutzers in Bereichssprache: was dessen Agenten per Auftrag bekommen dürfen (nur Admin). */
export function OwnerGrantsAreas({ username }: { username: string }) {
  const { t } = useTranslation("agents")
  return <PoolAreasEditor path={`/admin/tool-grants/${encodeURIComponent(username)}`}
    title={t("areas.owner_title")} hint={t("areas.owner_hint")} />
}
