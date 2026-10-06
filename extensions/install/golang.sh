#!/usr/bin/env bash
set -euo pipefail

info()    { echo "[INFO] $*"; }
success() { echo "[OK] $*"; }
warn()    { echo "[WARN] $*"; }
die()     { echo "[ERROR] $*" >&2; exit 1; }

# C/C++-Toolchain für cgo-Projekte (z.B. Go-Code mit "#cgo LDFLAGS: -lcryptopp").
# Ohne diese Pakete scheitert ein unverpacktes `go test ./...` beim Linken.
# Einzige Quelle der Liste: update.sh ruft dieses Script mit --deps-only auf,
# damit bestehende Go-Installationen die Pakete beim HydraHive-Update bekommen.
CGO_PACKAGES=(build-essential pkg-config libcrypto++-dev)

install_cgo_deps() {
    local missing=() p
    for p in "${CGO_PACKAGES[@]}"; do
        dpkg -s "$p" 2>/dev/null | grep -q "^Status: install ok installed" || missing+=("$p")
    done
    if [ "${#missing[@]}" -eq 0 ]; then
        success "cgo-Pakete vorhanden (${CGO_PACKAGES[*]})"
        return 0
    fi
    info "Installiere cgo-Pakete: ${missing[*]}"
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${missing[@]}"
    success "cgo-Pakete installiert: ${missing[*]}"
}

install_cgo_deps
if [ "${1:-}" = "--deps-only" ]; then
    exit 0
fi

ARCH="$(dpkg --print-architecture 2>/dev/null || uname -m)"
case "${ARCH}" in
  amd64|x86_64)  GO_ARCH="amd64" ;;
  arm64|aarch64) GO_ARCH="arm64" ;;
  *)             die "Unbekannte Architektur: ${ARCH}" ;;
esac

# Neueste stabile Go-Version von go.dev
GO_VERSION="$(curl -sf 'https://go.dev/dl/?mode=json' \
    | python3 -c "import sys,json; data=json.load(sys.stdin); stable=[r for r in data if not r['stable']==False]; print(stable[0]['version'])" 2>/dev/null \
    || echo "go1.24.3")"
info "Installiere ${GO_VERSION} (${GO_ARCH})..."

# Schon installiert und aktuell?
if [ -x /usr/local/go/bin/go ]; then
    INSTALLED="$(/usr/local/go/bin/go version 2>/dev/null | grep -oP 'go[0-9]+\.[0-9]+\.[0-9]+' || echo "")"
    if [ "${INSTALLED}" = "${GO_VERSION}" ]; then
        success "Go ${INSTALLED} bereits aktuell"
        exit 0
    fi
    info "Update von ${INSTALLED} auf ${GO_VERSION}..."
    rm -rf /usr/local/go
fi

TARBALL="${GO_VERSION}.linux-${GO_ARCH}.tar.gz"
URL="https://go.dev/dl/${TARBALL}"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

info "Download: ${URL}"
curl -fsSL -o "${TMP}/${TARBALL}" "${URL}" || die "Download fehlgeschlagen"

info "Entpacke nach /usr/local/go..."
tar -C /usr/local -xzf "${TMP}/${TARBALL}"

# Symlinks nach /usr/local/bin damit go/gofmt im PATH der Agents liegt
for BIN in go gofmt; do
    ln -sf "/usr/local/go/bin/${BIN}" "/usr/local/bin/${BIN}"
done

# Profile für Login-Shells (Bonus)
cat > /etc/profile.d/golang.sh <<'PROFILE'
export PATH="$PATH:/usr/local/go/bin"
export GOPATH="/root/go"
PROFILE
chmod 644 /etc/profile.d/golang.sh

INSTALLED_VER="$(/usr/local/go/bin/go version)"
success "Go installiert: ${INSTALLED_VER}"
