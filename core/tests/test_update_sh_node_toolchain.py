from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "installer" / "update.sh"


def test_update_repairs_missing_npm_even_when_node_is_new_enough() -> None:
    text = SCRIPT.read_text()

    node_check = text.index('log "Node.js prüfen"')
    npm_check = text.index('if ! command -v npm')
    frontend = text.index('log "Frontend neu bauen"')
    assert node_check < npm_check < frontend


def test_missing_npm_uses_pinned_corepack_version_with_apt_fallback() -> None:
    text = SCRIPT.read_text()

    assert "corepack prepare npm@11.6.2 --activate" in text
    assert 'apt-get install -y npm' in text
    assert 'command -v npm >/dev/null 2>&1 || err' in text
