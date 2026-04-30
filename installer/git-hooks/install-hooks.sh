#!/usr/bin/env bash
# Verlinkt die git-hooks aus diesem Verzeichnis nach .git/hooks/.
# Hooks selbst sind nicht git-tracked (per design), deshalb dieser
# Bootstrap-Schritt nach jedem clone / checkout.
#
# Aufruf: bash installer/git-hooks/install-hooks.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK_DIR="$REPO_ROOT/.git/hooks"
SRC_DIR="$REPO_ROOT/installer/git-hooks"

if [ ! -d "$HOOK_DIR" ]; then
  echo "Fehler: $HOOK_DIR nicht gefunden — git-Repo?" >&2
  exit 1
fi

for hook in pre-commit; do
  src="$SRC_DIR/$hook"
  dest="$HOOK_DIR/$hook"
  if [ ! -f "$src" ]; then
    continue
  fi
  ln -sf "../../installer/git-hooks/$hook" "$dest"
  chmod +x "$src"
  echo "Hook installiert: $hook → $src"
done
