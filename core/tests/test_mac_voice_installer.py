"""installer/modules-mac/55-voice.sh (Plan docs/plans/mac-voice.md): Whisper + Piper direkt auf dem Mac.

Nachgebauter Mac: Schein-Python legt venvs an, deren pip die Pakete nur aufzeichnet; launchctl/sudo/chown sind
Aufzeichnungen; die Bereitschaftsprüfung (Wyoming „describe“) wird über HH_VOICE_PROBE ersetzt.
"""
from __future__ import annotations

import os
import plistlib
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[2] / "installer"
SCRIPT = INSTALLER / "modules-mac" / "55-voice.sh"

STT_PINS = ["wyoming-faster-whisper==3.8.1", "faster-whisper==1.2.1", "ctranslate2==4.8.3", "av==17.1.0",
            "onnxruntime==1.23.2", "pysilero-vad==3.4.0", "wyoming==1.10.2"]
TTS_PINS = ["wyoming-piper==2.5.2", "piper-tts==1.8.0", "onnxruntime==1.23.2", "wyoming==1.10.2"]


def _exe(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(0o755)


@pytest.fixture
def mac(tmp_path: Path) -> dict:
    bin_ = tmp_path / "bin"
    calls = tmp_path / "calls.log"
    calls.write_text("")
    log = f'echo "$(basename "$0") $*" >> "{calls}"\n'
    # Schein-Python: „-m venv DIR“ legt DIR/bin/{pip,python,wyoming-faster-whisper} an; pip zeichnet auf.
    pip = f'#!/bin/bash\necho "pip $*" >> "{calls}"\n[ -f "{tmp_path}/pip-fails" ] && exit 1\nexit 0\n'
    _exe(tmp_path / "py" / "python3.12", log + f'''
if [ "$1" = "-m" ] && [ "$2" = "venv" ]; then
  d="${{@: -1}}"; mkdir -p "$d/bin"
  cat > "$d/bin/pip" <<'EOS'
{pip}EOS
  printf '#!/bin/bash\\nexit 0\\n' > "$d/bin/python"
  chmod 755 "$d/bin/pip" "$d/bin/python"
  exit 0
fi
[ "$1" = "--version" ] && echo "Python ${{FAKE_PY_VERSION:-3.12.13}}"
exit 0
''')
    _exe(bin_ / "sudo", log + 'exec "$@"\n')
    _exe(bin_ / "launchctl", log + f'case "$1" in list) for l in $(cat "{tmp_path}/running" 2>/dev/null); do '
                                   'echo "55 0 $l"; done;; esac\nexit 0\n')
    _exe(bin_ / "chown", log)
    _exe(bin_ / "id", 'if [ "$#" -eq 1 ] && [ "$1" = "-u" ]; then echo 0; else exec /usr/bin/id "$@"; fi\n')
    _exe(tmp_path / "probe", f'echo "probe $*" >> "{calls}"\n[ -f "{tmp_path}/probe-fails" ] && exit 1\nexit 0\n')
    return {"tmp": tmp_path, "bin": bin_, "calls": calls, "root": tmp_path / "voiceroot",
            "data": tmp_path / "data", "conf": tmp_path / "etc" / "install.conf",
            "stt_plist": tmp_path / "io.hydrahive.voice-stt.plist",
            "tts_plist": tmp_path / "io.hydrahive.voice-tts.plist", "python": tmp_path / "py" / "python3.12"}


def _run(m: dict, **extra) -> subprocess.CompletedProcess:
    (m["tmp"] / "etc").mkdir(exist_ok=True)
    env = {**os.environ, "PATH": f"{m['bin']}:/usr/bin:/bin", "HH_USER": "tester", "HH_VOICE_WAIT": "2",
           "HH_CONFIG_DIR": str(m["tmp"] / "etc"), "HH_DATA_DIR": str(m["data"]), "HH_LOG_DIR": str(m["tmp"] / "log"),
           "HH_VOICE_ROOT": str(m["root"]), "HH_VOICE_PYTHON": str(m["python"]),
           "HH_VOICE_STT_PLIST": str(m["stt_plist"]), "HH_VOICE_TTS_PLIST": str(m["tts_plist"]),
           "HH_VOICE_PROBE": str(m["tmp"] / "probe"), **extra}
    return subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True, timeout=60)


def _calls(m: dict) -> list[str]:
    return m["calls"].read_text().splitlines()


def _pip_installs(m: dict) -> list[str]:
    return [c for c in _calls(m) if c.startswith("pip install") and "--upgrade pip" not in c]


# --- Pakete --------------------------------------------------------------------------------------------------

def test_installs_pinned_packages_binary_only(mac):
    r = _run(mac, HH_VOICE_ARCH="x86_64")
    assert r.returncode == 0, r.stdout + r.stderr
    stt, tts = _pip_installs(mac)
    for pin in STT_PINS:
        assert pin in stt.split(), pin
    for pin in TTS_PINS:
        assert pin in tts.split(), pin
    # Nur fertige Pakete – einzige Ausnahme pysilero-vad (für Intel-Mac nur Quellcode)
    assert "--only-binary=:all:" in stt and "--no-binary=pysilero-vad" in stt
    assert "--only-binary=:all:" in tts and "--no-binary" not in tts


def test_second_run_skips_pip(mac):
    _run(mac)
    (mac["tmp"] / "running").write_text("io.hydrahive.voice-stt io.hydrahive.voice-tts")
    mac["calls"].write_text("")
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _pip_installs(mac) == []
    assert not any(c.startswith(("launchctl load", "launchctl unload")) for c in _calls(mac))


def test_changed_pins_reinstall(mac):
    _run(mac)
    (mac["root"] / "stt" / ".hh-pins").write_text("alt\n")
    (mac["tmp"] / "running").write_text("io.hydrahive.voice-stt io.hydrahive.voice-tts")
    mac["calls"].write_text("")
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    installs = _pip_installs(mac)
    assert len(installs) == 1 and "wyoming-faster-whisper==3.8.1" in installs[0]
    assert f"launchctl load {mac['stt_plist']}" in _calls(mac)
    assert f"launchctl load {mac['tts_plist']}" not in _calls(mac)


def test_pip_failure_aborts_without_daemons(mac):
    (mac["tmp"] / "pip-fails").write_text("")
    r = _run(mac)
    assert r.returncode != 0
    assert not mac["stt_plist"].exists() and not mac["tts_plist"].exists()
    assert not (mac["root"] / "stt" / ".hh-pins").exists()
    assert not (mac["root"] / "stt").exists()                  # halbes venv weg → nächster Lauf beginnt sauber
    assert "HH_INSTALL_VOICE=yes" not in (mac["conf"].read_text() if mac["conf"].exists() else "")


def test_stopped_daemon_gets_loaded(mac):
    _run(mac)
    (mac["tmp"] / "running").write_text("io.hydrahive.voice-tts")      # nur Piper läuft
    mac["calls"].write_text("")
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    calls = _calls(mac)
    assert f"launchctl load {mac['stt_plist']}" in calls
    assert f"launchctl load {mac['tts_plist']}" not in calls
    assert _pip_installs(mac) == []


def test_wrong_python_aborts(mac):
    r = _run(mac, FAKE_PY_VERSION="3.11.9")
    assert r.returncode != 0
    assert "3.12" in r.stderr
    assert _pip_installs(mac) == []


def test_missing_python_aborts(mac):
    r = _run(mac, HH_VOICE_PYTHON=str(mac["tmp"] / "fehlt"))
    assert r.returncode != 0
    assert not mac["stt_plist"].exists()


# --- Dienste -------------------------------------------------------------------------------------------------

def _plist(path: Path) -> dict:
    return plistlib.loads(path.read_bytes())


def test_daemons_run_as_service_user_on_localhost_only(mac):
    r = _run(mac)
    assert r.returncode == 0, r.stdout + r.stderr
    for path, label, port in ((mac["stt_plist"], "io.hydrahive.voice-stt", "10300"),
                              (mac["tts_plist"], "io.hydrahive.voice-tts", "10200")):
        p = _plist(path)
        assert p["Label"] == label
        assert p["UserName"] == "tester"                        # kein root
        assert p["RunAtLoad"] is True and p["KeepAlive"] is True
        args = p["ProgramArguments"]
        assert f"tcp://127.0.0.1:{port}" in args
        assert not any("0.0.0.0" in a for a in args)
        assert f"launchctl load {path}" in _calls(mac)


def test_stt_parameters_match_linux(mac):
    _run(mac)
    args = _plist(mac["stt_plist"])["ProgramArguments"]
    assert args[0] == str(mac["root"] / "stt" / "bin" / "wyoming-faster-whisper")
    joined = " ".join(args)
    for part in ("--model small", "--compute-type int8", "--beam-size 1", "--vad-filter",
                 f"--data-dir {mac['data']}/voice/stt"):
        assert part in joined, part
    assert "--initial-prompt" in args


def test_tts_parameters_match_linux(mac):
    _run(mac)
    args = _plist(mac["tts_plist"])["ProgramArguments"]
    assert args[:3] == [str(mac["root"] / "tts" / "bin" / "python"), "-m", "wyoming_piper"]
    joined = " ".join(args)
    assert "--voice de_DE-thorsten-medium" in joined
    assert f"--data-dir {mac['data']}/voice/tts" in joined
    assert f"--download-dir {mac['data']}/voice/tts" in joined


def test_model_dirs_belong_to_service_user(mac):
    _run(mac)
    calls = _calls(mac)
    for sub in ("stt", "tts"):
        assert (mac["data"] / "voice" / sub).is_dir()
        assert any(c.startswith("chown") and "tester" in c and f"voice/{sub}" in c for c in calls), sub


def test_daemon_home_is_writable_by_service_user(mac):
    """Befund Mac 22.10.: HOME lag im root-Ordner voice/ → huggingface_hub konnte seinen Cache nicht anlegen
    („Permission denied“), Whisper startete nie. HOME/Arbeitsordner müssen dem Dienstnutzer gehören."""
    _run(mac)
    calls = _calls(mac)
    for path in (mac["stt_plist"], mac["tts_plist"]):
        p = _plist(path)
        home = p["EnvironmentVariables"]["HOME"]
        assert p["WorkingDirectory"] == home
        assert any(c.startswith("chown") and "tester" in c and c.endswith(home) for c in calls), home
        assert p["EnvironmentVariables"].get("HF_HOME", "").startswith(home)


def test_waits_until_whisper_answers(mac):
    r = _run(mac)
    assert r.returncode == 0
    assert any(c.startswith("probe") and "10300" in c for c in _calls(mac))


def test_whisper_never_ready_fails(mac):
    (mac["tmp"] / "probe-fails").write_text("")
    r = _run(mac)
    assert r.returncode != 0
    assert "hydrahive2-voice-stt.log" in r.stderr
    assert "HH_INSTALL_VOICE=yes" not in (mac["conf"].read_text() if mac["conf"].exists() else "")


# --- Wunsch merken -------------------------------------------------------------------------------------------

def test_install_conf_marks_wanted(mac):
    mac["conf"].parent.mkdir(parents=True, exist_ok=True)
    mac["conf"].write_text("HH_INSTALL_TAILSCALE=yes\nHH_INSTALL_VOICE=no\n")
    _run(mac)
    lines = mac["conf"].read_text().splitlines()
    assert "HH_INSTALL_TAILSCALE=yes" in lines
    assert lines.count("HH_INSTALL_VOICE=yes") == 1 and "HH_INSTALL_VOICE=no" not in lines


# --- Grenzen -------------------------------------------------------------------------------------------------

def test_no_linux_tools_and_linux_untouched():
    text = SCRIPT.read_text()
    for bad in ("apt-get", "systemctl", "incus ", "docker"):
        assert bad not in text, bad
    for f in (INSTALLER / "install.sh", INSTALLER / "update.sh", INSTALLER / "modules" / "55-voice.sh"):
        assert "modules-mac/55-voice" not in f.read_text()


def test_apple_silicon_needs_no_compiler(mac):
    """Apple-Mac: pysilero-vad gibt es fertig (macosx_11_0_arm64) – nichts selbst bauen. Sonst hinge Voice an Apples
    Kommandozeilenwerkzeugen, die beim Tester (macOS 27) nicht zum SDK passten (Befund 23.10.2026, Tailscale)."""
    r = _run(mac, HH_VOICE_ARCH="arm64")
    assert r.returncode == 0, r.stdout + r.stderr
    stt, _ = _pip_installs(mac)
    assert "--only-binary=:all:" in stt and "--no-binary" not in stt


def test_intel_still_builds_pysilero(mac):
    r = _run(mac, HH_VOICE_ARCH="x86_64")
    assert r.returncode == 0, r.stdout + r.stderr
    stt, _ = _pip_installs(mac)
    assert "--no-binary=pysilero-vad" in stt
