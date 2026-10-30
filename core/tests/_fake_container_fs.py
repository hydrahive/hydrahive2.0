"""Attrappe für Container-Dateien (tests/test_project_container_files.py): kleines Dateisystem im Speicher,
beantwortet realpath/cat/Schreiben wie `incus exec` im Container."""
from __future__ import annotations

import posixpath


class FakeContainer:
    """Mini-Dateisystem im Container: files[pfad] = bytes, links[pfad] = ziel."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {"/work/a.txt": b"eins\nzwei\ndrei\n", "/etc/passwd": b"root:x:0:0\n"}
        self.dirs = {"/", "/work", "/etc", "/work/sub", "/workshop"}
        self.files["/workshop/geheim.txt"] = b"nachbar\n"
        self.realpath_fails = False
        self.links: dict[str, str] = {"/work/raus": "/etc", "/work/pw": "/etc/passwd"}
        self.calls: list[list[str]] = []

    def _real(self, p: str, must_exist: bool) -> str | None:
        parts = [x for x in p.split("/") if x]
        cur = "/"
        for i, part in enumerate(parts):
            cur = posixpath.normpath(posixpath.join(cur, part))
            for _ in range(10):
                if cur in self.links:
                    cur = self.links[cur]
                else:
                    break
            last = i == len(parts) - 1
            if not last and cur not in self.dirs:
                return None
            if last and must_exist and cur not in self.files and cur not in self.dirs:
                return None
        return cur

    async def run(self, args: list[str], stdin: bytes | None) -> tuple[int, bytes, bytes]:
        self.calls.append(list(args))
        assert args[0] == "incus"
        if args[1] == "exec":
            i = args.index("--")
            cmd = args[i + 1:]
            if cmd[0] == "realpath":
                flag, path = cmd[1], cmd[-1]
                if self.realpath_fails:                      # z. B. Container-Fehler: rc≠0, aber Text auf stdout
                    return 1, b"/work/a.txt\n", b"Fehler"
                r = self._real(path, must_exist=(flag == "-e"))
                if flag == "-m" and r is None:
                    r = posixpath.normpath(path if path.startswith("/") else "/work/" + path)
                return (0, (r + "\n").encode(), b"") if r else (1, b"", b"No such file")
            if cmd[0] == "cat":
                path = cmd[-1]
                if path in self.files:
                    return 0, self.files[path], b""
                return 1, b"", b"No such file"
            if cmd[0] == "sh" and 'mv -f "$t" "$1"' in cmd[2]:
                target = cmd[-1]
                parent = posixpath.dirname(target)
                self.dirs.add(parent)
                self.files[target] = stdin or b""
                return 0, b"", b""
            if cmd[0] == "test":
                return (0, b"", b"") if cmd[-1] in self.files else (1, b"", b"")
        return 1, b"", b"unbekannt"
