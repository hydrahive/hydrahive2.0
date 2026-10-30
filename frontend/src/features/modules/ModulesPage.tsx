import { AdminRedirect } from "@/features/cockpit/admin/AdminRedirect"

/** Alte Modul-Seite: nur noch Umleitung ins Admin-Fenster „Module“ (Plan alte-seiten-umleiten). */
export function ModulesPage() {
  return <AdminRedirect section="modules" />
}
