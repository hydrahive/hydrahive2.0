#!/bin/sh
# Reproducible, opt-in builder for the temporary Game Studio PR-0 proof image.
set -eu

: "${HH_GAME_GODOT_BINARY:?absolute Godot binary path required}"
: "${HH_GAME_GODOT_SHA256:?Godot binary sha256 required}"

ALIAS="${HH_GAME_IMAGE_ALIAS:-hh-game-proof-godot-4.4.1}"
SOURCE_IMAGE="${HH_GAME_SOURCE_IMAGE:-images:ubuntu/24.04/cloud}"
BRIDGE="${HH_GAME_BUILDER_BRIDGE:-br0}"
NAME="hh-game-proof-builder-$$"
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
FIXTURE="$HERE/fixtures/game_runtime_godot"

case "$HH_GAME_GODOT_BINARY" in /*) ;; *) echo "Godot path must be absolute" >&2; exit 2 ;; esac
[ -x "$HH_GAME_GODOT_BINARY" ] || { echo "Godot binary is not executable" >&2; exit 2; }
printf '%s  %s\n' "$HH_GAME_GODOT_SHA256" "$HH_GAME_GODOT_BINARY" | sha256sum -c -
command -v incus >/dev/null
[ -r /dev/kvm ] && [ -w /dev/kvm ] || { echo "KVM unavailable" >&2; exit 2; }
[ -f "$FIXTURE/project.godot" ] || { echo "Godot fixture missing" >&2; exit 2; }
if incus image list "$ALIAS" --format=csv -c f | grep -q .; then
    echo "Image alias already exists: $ALIAS" >&2
    exit 2
fi

instance_exists() {
    incus list "$NAME" --format=json | python3 -c \
        'import json,sys; n=sys.argv[1]; raise SystemExit(0 if any(x.get("name")==n for x in json.load(sys.stdin)) else 1)' "$NAME"
}
cleanup() {
    attempts=0
    while instance_exists; do
        attempts=$((attempts + 1))
        incus delete "$NAME" --force >/dev/null 2>&1 || true
        [ "$attempts" -lt 3 ] || break
        sleep 1
    done
    ! instance_exists
}
finish() {
    status=$?
    trap - EXIT INT TERM
    cleanup || status=99
    exit "$status"
}
trap finish EXIT INT TERM

incus init --vm -c limits.cpu=2 -c limits.memory=2048MiB -d root,size=10GiB -- "$SOURCE_IMAGE" "$NAME"
SOURCE_FINGERPRINT=$(incus list "$NAME" --format=json | python3 -c \
    'import json,sys; print(json.load(sys.stdin)[0]["expanded_config"]["volatile.base_image"])')
incus start "$NAME"
i=0
until incus exec "$NAME" -- /bin/true >/dev/null 2>&1; do
    i=$((i + 1)); [ "$i" -lt 90 ] || { echo "guest agent timeout" >&2; exit 1; }; sleep 2
done
incus config device add "$NAME" eth0 nic nictype=bridged parent="$BRIDGE"
incus restart "$NAME"
i=0
until incus exec "$NAME" -- /usr/bin/getent hosts archive.ubuntu.com >/dev/null 2>&1; do
    i=$((i + 1)); [ "$i" -lt 90 ] || { echo "builder network timeout" >&2; exit 1; }; sleep 2
done

incus exec "$NAME" -- env DEBIAN_FRONTEND=noninteractive apt-get update -qq
incus exec "$NAME" -- env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
    xvfb xauth libgl1-mesa-dri libglx-mesa0 mesa-utils fontconfig \
    libxcursor1 libxi6 libxinerama1 libxext6 libx11-6 libasound2t64
PACKAGE_SHA256=$(incus exec "$NAME" -- /bin/sh -c \
    "dpkg-query -W -f='\${Package}=\${Version}\\n' | sort | sha256sum | cut -d' ' -f1")
incus file push "$HH_GAME_GODOT_BINARY" "$NAME/usr/local/bin/godot"
incus exec "$NAME" -- chmod 0755 /usr/local/bin/godot
incus exec "$NAME" -- mkdir -p /opt/game
for file in project.godot main.tscn main.gd export_presets.cfg; do
    incus file push "$FIXTURE/$file" "$NAME/opt/game/$file"
done
incus exec "$NAME" -- xvfb-run -a /usr/local/bin/godot --path /opt/game \
    --rendering-method gl_compatibility --audio-driver Dummy --quit-after 2

# The published proof image is deliberately networkless.
incus config device remove "$NAME" eth0
incus list "$NAME" --format=json | python3 -c \
    'import json,sys; d=json.load(sys.stdin)[0]; assert "eth0" not in d["expanded_devices"]'
incus stop "$NAME" --force
incus publish "$NAME" --alias "$ALIAS" \
    "game-proof.source-image=$SOURCE_FINGERPRINT" \
    "game-proof.godot-sha256=$HH_GAME_GODOT_SHA256" \
    "game-proof.packages-sha256=$PACKAGE_SHA256"
incus image list "$ALIAS" --format=json | python3 -c \
    'import json,sys; d=json.load(sys.stdin)[0]; print("IMAGE_FINGERPRINT="+d["fingerprint"]); print("IMAGE_SIZE="+str(d["size"]))'
printf 'SOURCE_IMAGE_FINGERPRINT=%s\nPACKAGE_MANIFEST_SHA256=%s\n' "$SOURCE_FINGERPRINT" "$PACKAGE_SHA256"
