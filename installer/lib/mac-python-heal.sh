#!/usr/bin/env bash
# Python-Pakete im venv heil machen (macOS-Update, docs/specs/mac-update.md §2.2).
#
# `pip install -e core` prüft nur die Versionsgrenzen. Ein beschädigtes oder halb aktualisiertes Paket bleibt
# liegen (Befund 20.10.2026: LiteLLM mit neuer main.py und alter Handler-Datei → jeder Modellaufruf scheiterte).
# Darum: `pip check` auswerten und nur die gemeldeten Pakete mit --force-reinstall --no-deps neu holen;
# LiteLLM zusätzlich, wenn sein Import scheitert (gemischte Dateien sieht pip check nicht).
#
# Aufruf: hh_mac_heal_python <venv-bin> <nutzer> <log>   (wird von update-mac.sh mit `source` geladen)

hh_mac_heal_python() {
  local venv_bin="$1" user="$2" log_file="$3"
  local broken=() out name
  out="$(sudo -u "$user" "$venv_bin/pip" check 2>&1)" || true
  printf '%s\n' "$out" >> "$log_file"
  # Zeilen wie „<paket> <version> has requirement …“ / „<paket> <version> is not supported …“
  while IFS= read -r name; do
    [[ "$name" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || continue
    case " ${broken[*]} " in *" $name "*) ;; *) broken+=("$name") ;; esac
  done < <(printf '%s\n' "$out" | awk '/ has requirement | is not supported | requires / {print $1}')
  if ! sudo -u "$user" "$venv_bin/python" -c "import litellm" >> "$log_file" 2>&1; then
    printf '[%s] LiteLLM lässt sich nicht laden – wird neu installiert\n' "$(date '+%Y-%m-%d %H:%M:%S')" >> "$log_file"
    case " ${broken[*]} " in *" litellm "*) ;; *) broken+=("litellm") ;; esac
  fi
  for name in "${broken[@]}"; do
    printf '[%s] Paket %s neu installieren\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$name" >> "$log_file"
    sudo -u "$user" "$venv_bin/pip" install --force-reinstall --no-deps "$name" >> "$log_file" 2>&1 \
      || printf '[%s] Neuinstallation von %s fehlgeschlagen\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$name" >> "$log_file"
  done
  return 0
}
