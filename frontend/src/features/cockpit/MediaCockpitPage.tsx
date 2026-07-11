import { AtelierPage } from "@/modules/atelier/AtelierPage"

/**
 * Recovery entry for the proven trailer workflow.
 *
 * Keep /media focused on the connected Atelier pipeline: character selection,
 * image generation, gallery, video clips and film rendering. The newer
 * file-based media workspaces remain persisted and can be reintegrated only
 * after their workflow has been validated separately.
 */
export function MediaCockpitPage() {
  return <AtelierPage />
}
