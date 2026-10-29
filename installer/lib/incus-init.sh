#!/usr/bin/env bash
# incus nur einrichten, wenn es noch gar keinen Speicher gibt (docs/specs/incus-init-update.md).
#
# Wird von update.sh (Prüfung) und modules/70-containers.sh (Einrichtung) genutzt. Erwartet eine log()-Funktion.
# Der Name des Speichers spielt keine Rolle: Nach einem Umzug heißt er z. B. „ssd“ – das ist eingerichtet.

# Gibt die Speicher (eine Zeile je Speicher) aus. Rückgabe ≠ 0, wenn incus nicht antwortet.
_incus_pools() {
  incus storage list -f csv 2>/dev/null
}

# 0 = incus antwortet und hat mindestens einen Speicher.
incus_is_initialized() {
  local pools
  pools="$(_incus_pools)" || return 1
  [ -n "${pools//[[:space:]]/}" ]
}

# Richtet incus ein, wenn es antwortet und noch keinen Speicher hat. Überschreibt nie einen bestehenden Speicher
# oder das Profil eines eingerichteten incus.
ensure_incus_initialized() {
  local pools
  if ! pools="$(_incus_pools)"; then
    log "incus antwortet nicht – Einrichtung übersprungen (nichts geändert)"
    return 0
  fi
  if [ -n "${pools//[[:space:]]/}" ]; then
    log "incus ist schon eingerichtet – Speicher und Profil bleiben unverändert"
    return 0
  fi
  log "incus initialisieren (dir-Storage, kein Bridge-Auto-Setup)"
  incus admin init --preseed <<'PRESEED'
config: {}
networks: []
storage_pools:
- config: {}
  description: ""
  name: default
  driver: dir
profiles:
- config: {}
  description: ""
  devices:
    root:
      path: /
      pool: default
      type: disk
  name: default
projects: []
cluster: null
PRESEED
}
