#!/usr/bin/env bash
# Git-Schritt des Updates – verwirft nichts still, bleibt auf dem eigenen Branch.
# docs/specs/update-git-sicher.md (Task cabd0df1).
#
# Erwartet: log, err (aus update.sh) und HH_GIT (git-Aufruf, in update.sh als
# Dienstnutzer mit safe.directory). Vorher galt: scheiterte `pull --ff-only`,
# folgte `reset --hard origin/main` – lokale Änderungen weg, Branch auf main.

# Einzige Datei, die das Update selbst verändern darf (npm schrieb sie früher um).
HH_GIT_SELF_OWNED="frontend/package-lock.json"

hh_git_update() {
  local repo=$1 branch remote before_remote dirty ahead
  cd "$repo"

  branch=$($HH_GIT symbolic-ref --quiet --short HEAD) \
    || err "Kein Branch ausgecheckt (losgelöster Stand) – Update angehalten, nichts verändert."
  remote="origin/$branch"

  # Von uns selbst umgeschriebene Lock-Datei zurück auf den Stand im Repo.
  if ! $HH_GIT diff --quiet -- "$HH_GIT_SELF_OWNED" 2>/dev/null; then
    log "$HH_GIT_SELF_OWNED zurück auf den Repo-Stand (vom letzten Update umgeschrieben)"
    $HH_GIT checkout -- "$HH_GIT_SELF_OWNED"
  fi

  dirty=$($HH_GIT status --porcelain --untracked-files=no)
  if [ -n "$dirty" ]; then
    err "Lokale Änderungen in: $(printf '%s' "$dirty" | awk '{print $NF}' | paste -sd ' ') – Update angehalten, nichts verworfen."
  fi

  before_remote=$($HH_GIT rev-parse --quiet --verify "refs/remotes/$remote" || true)
  $HH_GIT fetch --quiet origin "+refs/heads/$branch:refs/remotes/$remote" 2>&1 \
    || err "git fetch fehlgeschlagen ($remote) – Netzwerk oder Zugang prüfen."

  if $HH_GIT merge-base --is-ancestor HEAD "$remote"; then
    $HH_GIT merge --ff-only --quiet "$remote"
    return 0
  fi

  ahead=$($HH_GIT rev-list --count "$remote..HEAD")
  # Echter History-Rewrite auf GitHub: alle lokalen Commits stammen aus der alten origin-Geschichte.
  # (Wäre die alte Geschichte noch in der neuen enthalten, hätte oben schon das Vorspulen gegriffen.)
  if [ -n "$before_remote" ] && [ "$($HH_GIT rev-list --count "$before_remote..HEAD")" = 0 ]; then
    local tag
    tag="hh-update-vorher-$(date -u +%Y%m%d-%H%M%S)"
    $HH_GIT tag "$tag" HEAD
    log "Geschichte auf $remote wurde neu geschrieben – alter Stand gesichert als $tag, setze auf $remote"
    $HH_GIT reset --hard --quiet "$remote"
    return 0
  fi

  err "$ahead lokale Commits auf $branch, die $remote nicht hat – Update angehalten, nichts verworfen."
}
