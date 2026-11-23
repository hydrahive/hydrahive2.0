#!/usr/bin/env python3
"""Konsistente Sicherung einer laufenden SQLite-DB für das Update (docs/specs/update-rollback.md §3.1, Etappe U3).

Läuft mit dem System-python3 (nicht mit dem venv: das ist Gegenstand des Rückwegs) und nur mit der Standardbibliothek.

    db_snapshot.py estimate <db>          Nutzdaten in Bytes: (page_count - freelist_count) * page_size
    db_snapshot.py copy <db> <roh>        VACUUM INTO <roh> + quick_check   (als Besitzer der DB aufrufen)
    db_snapshot.py pack <roh> <ziel>      zstd (sonst gzip) -> fsync -> rename, <roh> wird entfernt (als root)
    db_snapshot.py snapshot <db> <ziel>   copy + pack in einem Schritt
    db_snapshot.py verify <ziel>          entpacken in eine Temp-Datei und quick_check (nur lesen)
    db_snapshot.py schema-version <db>    höchste Version in schema_version (nur lesen, 0 wenn leer)
    db_snapshot.py restore <ziel> <db> [besitzer]
                                          Rückweg: entpacken, quick_check, als <db>.neu mit O_EXCL|O_NOFOLLOW schreiben
                                          (nie in einen vorhandenen Link), Besitzer setzen, fsync, rename auf <db>.
                                          Weigert sich, wenn <db> noch existiert (der kaputte Stand wird vorher zur Seite
                                          gelegt, nie überschrieben).

``copy`` läuft als Besitzer der DB, nicht als root: Öffnet root eine WAL-DB bei gestopptem Dienst, legt er ``-wal`` und
``-shm`` root-eigen an, und der Dienst startet danach nicht mehr.

Warum VACUUM INTO und nicht `sqlite3 .backup`: Die CLI startet die Kopie bei jeder Schreibung des laufenden Dienstes
neu und wird nie fertig (Messung .4). VACUUM INTO liest einen konsistenten Snapshot und liefert eine kompakte Datei.
Die Quelle wird nur lesend geöffnet. Exit 0 = ok, 2 = Fehler (Grund auf stderr, in einer Zeile).
"""
from __future__ import annotations

import gzip
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote


class SnapshotError(RuntimeError):
    pass


def _open_ro(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise SnapshotError(f"{path} existiert nicht")
    return sqlite3.connect(f"file:{quote(str(path))}?mode=ro", uri=True, timeout=60)


def estimate(db: Path) -> int:
    con = _open_ro(db)
    try:
        pages = con.execute("PRAGMA page_count").fetchone()[0]
        free = con.execute("PRAGMA freelist_count").fetchone()[0]
        size = con.execute("PRAGMA page_size").fetchone()[0]
    finally:
        con.close()
    return max(pages - free, 0) * size


def _quick_check(path: Path) -> None:
    con = sqlite3.connect(f"file:{quote(str(path))}?mode=ro", uri=True)
    try:
        rows = [r[0] for r in con.execute("PRAGMA quick_check").fetchall()]
    finally:
        con.close()
    if rows != ["ok"]:
        raise SnapshotError(f"quick_check: {'; '.join(map(str, rows))[:200]}")


def _fsync(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _compress(src: Path, dest_tmp: Path) -> None:
    if dest_tmp.name.endswith(".zst.tmp"):
        zstd = shutil.which("zstd")
        r = subprocess.run([zstd, "-3", "-T0", "-q", "-f", "-o", str(dest_tmp), str(src)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SnapshotError(f"zstd: {r.stderr.strip()[:200]}")
        return
    with open(src, "rb") as f_in, gzip.open(dest_tmp, "wb", compresslevel=6) as f_out:
        shutil.copyfileobj(f_in, f_out, 1 << 20)


def _decompress(src: Path, out: Path) -> None:
    if src.name.endswith(".zst"):
        r = subprocess.run(["zstd", "-d", "-q", "-f", "-o", str(out), str(src)], capture_output=True, text=True)
        if r.returncode != 0:
            raise SnapshotError(f"zstd -d: {r.stderr.strip()[:200]}")
        return
    with gzip.open(src, "rb") as f_in, open(out, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out, 1 << 20)


def copy(db: Path, raw: Path) -> None:
    """VACUUM INTO + quick_check. Bei einem Fehler bleibt keine ``raw`` zurück."""
    raw.unlink(missing_ok=True)
    try:
        con = _open_ro(db)
        try:
            con.execute("VACUUM INTO ?", (str(raw),))
        finally:
            con.close()
        _quick_check(raw)
    except SnapshotError:
        raw.unlink(missing_ok=True)
        raise
    except (sqlite3.Error, OSError) as exc:
        raw.unlink(missing_ok=True)
        raise SnapshotError(f"{type(exc).__name__}: {exc}") from exc


def pack(raw: Path, dest: Path) -> int:
    """``dest`` endet auf .zst oder .gz. Ein Fehler hinterlässt keine halbe ``dest``; ``raw`` wird immer entfernt."""
    tmp_out = dest.parent / (dest.name + ".tmp")
    tmp_out.unlink(missing_ok=True)
    if raw.is_symlink() or not raw.is_file():           # raw liegt in einem Ordner des DB-Besitzers: nie einem Link folgen
        raise SnapshotError(f"{raw} ist keine reguläre Datei")
    try:
        if dest.name.endswith(".zst") and not shutil.which("zstd"):
            raise SnapshotError("zstd nicht gefunden")
        _compress(raw, tmp_out)
        _fsync(tmp_out)
        os.replace(tmp_out, dest)
        _fsync(dest.parent)
        return dest.stat().st_size
    except SnapshotError:
        raise
    except OSError as exc:
        raise SnapshotError(f"{type(exc).__name__}: {exc}") from exc
    finally:
        tmp_out.unlink(missing_ok=True)
        raw.unlink(missing_ok=True)


def snapshot(db: Path, dest: Path) -> int:
    raw = dest.parent / ".snapshot.db.tmp"
    copy(db, raw)
    return pack(raw, dest)


def verify(snap: Path) -> None:
    if not snap.is_file():
        raise SnapshotError(f"{snap} existiert nicht")
    out = snap.parent / ".verify.db.tmp"
    out.unlink(missing_ok=True)
    try:
        _decompress(snap, out)
        _quick_check(out)
    except (sqlite3.Error, OSError, EOFError) as exc:
        raise SnapshotError(f"{type(exc).__name__}: {exc}") from exc
    finally:
        out.unlink(missing_ok=True)


def schema_version(db: Path) -> int:
    con = _open_ro(db)
    try:
        try:
            row = con.execute("SELECT MAX(version) FROM schema_version").fetchone()
        except sqlite3.OperationalError:
            return 0
    finally:
        con.close()
    return int(row[0] or 0) if row else 0


def restore(snap: Path, dest: Path, owner: str | None = None) -> None:
    """Spielt eine Sicherung als ``dest`` ein. Läuft als root: ``dest`` liegt in einem Ordner des Dienstnutzers."""
    if os.path.lexists(dest):
        raise SnapshotError(f"{dest} existiert noch – der kaputte Stand muss zuerst zur Seite gelegt werden")
    if not snap.is_file():
        raise SnapshotError(f"{snap} existiert nicht")
    work = snap.parent / ".restore.db.tmp"          # im root-eigenen Sicherungsordner, nicht beim Dienstnutzer
    work.unlink(missing_ok=True)
    neu = dest.parent / (dest.name + ".neu")
    try:
        _decompress(snap, work)
        _quick_check(work)
        uid = gid = None
        if owner and os.geteuid() == 0:
            import pwd
            try:
                pw = pwd.getpwnam(owner)
            except KeyError as exc:
                raise SnapshotError(f"Benutzer {owner} unbekannt") from exc
            uid, gid = pw.pw_uid, pw.pw_gid
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(neu, flags, 0o600)
        try:
            with open(work, "rb") as src, os.fdopen(os.dup(fd), "wb") as out:
                shutil.copyfileobj(src, out, 1 << 20)
                out.flush()
                os.fsync(out.fileno())
            if uid is not None:
                os.fchown(fd, uid, gid)
        finally:
            os.close(fd)
        os.rename(neu, dest)
        _fsync(dest.parent)
    except SnapshotError:
        raise
    except (sqlite3.Error, OSError, EOFError) as exc:
        raise SnapshotError(f"{type(exc).__name__}: {exc}") from exc
    finally:
        work.unlink(missing_ok=True)
        if os.path.lexists(neu) and not os.path.lexists(dest):
            neu.unlink(missing_ok=True)


def main(argv: list[str]) -> int:
    try:
        if len(argv) == 3 and argv[1] == "estimate":
            print(estimate(Path(argv[2])))
        elif len(argv) == 3 and argv[1] == "schema-version":
            print(schema_version(Path(argv[2])))
        elif len(argv) in (4, 5) and argv[1] == "restore":
            restore(Path(argv[2]), Path(argv[3]), argv[4] if len(argv) == 5 else None)
            print("ok")
        elif len(argv) == 4 and argv[1] == "copy":
            copy(Path(argv[2]), Path(argv[3]))
            print("ok")
        elif len(argv) == 4 and argv[1] == "pack":
            print(pack(Path(argv[2]), Path(argv[3])))
        elif len(argv) == 4 and argv[1] == "snapshot":
            print(snapshot(Path(argv[2]), Path(argv[3])))
        elif len(argv) == 3 and argv[1] == "verify":
            verify(Path(argv[2]))
            print("ok")
        else:
            print("Aufruf: db_snapshot.py estimate <db> | schema-version <db> | restore <ziel> <db> [besitzer] | copy <db> <roh> | pack <roh> <ziel.zst|.gz> | snapshot <db> <ziel> | verify <ziel>", file=sys.stderr)
            return 2
    except SnapshotError as exc:
        print(str(exc).replace("\n", " "), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
