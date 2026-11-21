import { useTranslation } from "react-i18next"
import { CatalogSwitch } from "./_CatalogSwitch"
import type { Peer } from "./types"

interface Props {
  peer: Peer
  onSetHub: (next: boolean) => void
  onSetAccept: (next: boolean) => void
}

// Föderations-Katalog (docs/specs/federation-catalog.md §Oberfläche, Reiter „Server“):
// „Als Hub verwenden“ (Client-Sicht) und „Katalog annehmen“ (Hub-Sicht) je Partner.
// Einschalten nur bei aktiver Kopplung; Ausschalten geht immer (Backend lässt es zu).
export function PeerCatalogToggles({ peer, onSetHub, onSetAccept }: Props) {
  const { t } = useTranslation("federation")
  const active = peer.status === "active"
  return (
    <div className="space-y-1.5 border-t border-white/[4%] pt-2.5">
      <p className="text-[11px] text-zinc-400">{t("catalog.peer_title")}</p>
      <div className="grid gap-2 sm:grid-cols-2">
        <CatalogSwitch
          checked={peer.is_hub}
          label={t("catalog.hub_toggle")}
          hint={t("catalog.hub_hint", { server: peer.name })}
          disabled={!active && !peer.is_hub}
          onChange={onSetHub}
        />
        <CatalogSwitch
          checked={peer.catalog_accept}
          label={t("catalog.accept_toggle")}
          hint={t("catalog.accept_hint", { server: peer.name })}
          disabled={!active && !peer.catalog_accept}
          onChange={onSetAccept}
        />
      </div>
      {!active && <p className="text-[11px] text-zinc-500">{t("catalog.only_active")}</p>}
    </div>
  )
}
