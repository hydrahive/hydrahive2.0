"""Schritte 2–5: messen, Platz prüfen, packen, prüfen (Spec archiv-system.md, Etappe 2).

Ein Agent oder eine Instanz → ein Paket unter agents/. Ein Projekt → ein Paket unter projects/.
Ein Nutzer → ein Paket unter users/ und je eigenem Projekt ein Projekt-Paket mit
`extra.part_of` (damit sich das Projekt später auch ohne den Nutzer wiederverwenden lässt).
"""
from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from hydrahive.archive import _bundle, package
from hydrahive.archive._paths import kind_dir
from hydrahive.archive._targets import ARCHIVE_KIND, REASON
from hydrahive.archive.verify import VerifyError, verify

Progress = Callable[[int], None]


def _agent_sources(work: Path, part: dict) -> tuple[list, set]:
    """Agent-Ordner + eigener Arbeitsordner; config.json aus dem Ordner wird durch die maskierte ersetzt."""
    from hydrahive.agents import config as agent_config
    pre = part["prefix"]
    sources = [(f"{pre}agent", Path(part["agent_dir"]))]
    if part.get("workspace"):
        sources.append((f"{pre}workspace", Path(part["workspace"])))
    skip = set()
    cfg = agent_config.get(part["id"])
    if cfg:
        masked = _bundle.masked_agent_config(work / "cfg" / part["id"], cfg)
        sources.append((f"{pre}agent/config.json", masked))
        skip.add(f"{pre}agent/config.json")
    return sources, skip


def _project_sources(work: Path, part: dict) -> tuple[list, set]:
    from hydrahive.projects import config as project_config
    w = work / "p" / part["id"]
    sources = [("project", Path(part["project_dir"])), ("workspace", Path(part["workspace"]))]
    skip = {"project/config.json"}
    cfg = project_config.get(part["id"])
    if cfg:
        sources.append(("project/config.json", _bundle.masked_project_config(w, cfg)))
    for a in part["agents"]:
        s, k = _agent_sources(w, a)
        sources += s
        skip |= k
    sources += _bundle.write_sessions(w, part["sessions"])
    return sources, skip


def _user_sources(work: Path, plan: dict) -> tuple[list, set]:
    from hydrahive.communication.discord.config import _config_file as discord_file
    from hydrahive.communication.whatsapp.config import _config_file as wa_file
    from hydrahive.credentials.store import _file_for
    from hydrahive.skills._paths import user_dir
    from hydrahive.zahnfee.storage import _path as zahnfee_file
    user = plan["user"]
    name = user["name"]
    w = work / "u"
    sources: list = [("user/user.json", _bundle.user_record(w, name)), ("credentials.json", _file_for(name)),
                     ("skills", user_dir(name)), ("whatsapp.json", wa_file(name)), ("zahnfee.json", zahnfee_file(name))]
    skip: set = set()
    for a in plan["agents"]:
        s, k = _agent_sources(w, a)
        sources += s
        skip |= k
    discord = _bundle.masked_discord(w, discord_file(name))
    if discord:
        sources.append(("discord.json", discord))
    rows = _bundle.user_rows(w, name, user["user_id"])
    if rows:
        sources.append(("db", rows))
    flows = _butler_flows(w, name)
    if flows:
        sources.append(("butler", flows))
    sources += _bundle.write_sessions(w, plan["sessions"])
    return sources, skip


def _butler_flows(work: Path, name: str) -> Path | None:
    from hydrahive.butler import persistence as butler
    flows = butler.list_flows(owner=name)
    if not flows:
        return None
    out = work / "butler"
    out.mkdir(parents=True, exist_ok=True)
    for f in flows:
        (out / f"{f.flow_id}.json").write_text(f.model_dump_json(indent=2), encoding="utf-8")
    return out


def measure(sources: list[tuple[str, Path]]) -> tuple[int, int]:
    """(Bytes, Dateien) ohne eingehängte Laufwerke und ohne Symlinks zu folgen."""
    total = files = 0
    for _arc, src in sources:
        src = Path(src)
        if src.is_file() and not src.is_symlink():
            total, files = total + src.stat().st_size, files + 1
            continue
        for root, dirs, names in os.walk(src, followlinks=False):
            dirs[:] = [d for d in dirs if not os.path.ismount(os.path.join(root, d))]
            for n in names:
                p = os.path.join(root, n)
                if not os.path.islink(p):
                    try:
                        total += os.lstat(p).st_size
                    except OSError:
                        continue
                files += 1
    return total, files


def bundles(plan: dict, work: Path) -> list[dict]:
    """Was gepackt wird, als Liste von Paketen. Das Haupt-Paket steht zuletzt (part_of zeigt darauf)."""
    out = []
    for part in plan["projects"]:
        sources, skip = _project_sources(work, part)
        extra = {"members": part["members"], "mounts_skipped": part["mounts"]}
        out.append({"kind": "projects", "name": part["name"], "source_id": part["id"], "owner": part["owner"],
                    "reason": REASON["project"], "sources": sources, "skip": skip, "extra": extra})
    if plan["kind"] in ("agent", "instance", "orphan_agent"):
        sources, skip = _agent_sources(work, plan["agents"][0])
        sources += _bundle.write_sessions(work / "a", plan["sessions"])
        if plan.get("user"):
            sources.append(("user/user.json", _bundle.user_record(work / "a", plan["user"]["name"])))
        out.append({"kind": ARCHIVE_KIND[plan["kind"]], "name": plan["name"], "source_id": plan["id"],
                    "owner": plan["owner"], "reason": REASON[plan["kind"]], "sources": sources, "skip": skip,
                    "extra": {}})
    elif plan["kind"] == "user":
        sources, skip = _user_sources(work, plan)
        out.append({"kind": "users", "name": plan["name"], "source_id": plan["user"]["user_id"],
                    "owner": plan["name"], "reason": REASON["user"], "sources": sources, "skip": skip,
                    "extra": {"projects": [p["id"] for p in plan["projects"]]}})
    return out


def pack_all(items: list[dict], on_file: Progress, on_target: Callable[[Path], None] | None = None) -> list[dict]:
    """Packt und prüft jedes Paket. Bei Fehlern: alle Pakete dieses Auftrags wieder weg, Fehler weiterreichen.
    `on_target` erfährt jeden Paketpfad vor dem Schreiben (für das Zurückrollen nach einem Neustart)."""
    done: list[dict] = []
    try:
        main = items[-1]
        for item in items:
            extra = dict(item["extra"])
            if item is not main and main["kind"] == "users":
                extra["part_of_user"] = main["source_id"]
            meta = package.pack(kind=item["kind"], name=item["name"], source_id=item["source_id"],
                                owner=item["owner"], reason=item["reason"], sources=item["sources"],
                                extra=extra, skip=item["skip"], on_file=on_file, on_target=on_target)
            done.append(meta)
            verify(kind_dir(meta["kind"]) / meta["file"])
        if main["kind"] == "users":
            link_parts(done)
        return done
    except BaseException:
        discard(done)
        raise


def link_parts(metas: list[dict]) -> None:
    """Projekt-Pakete eines Nutzers zeigen auf das Nutzer-Paket (extra.part_of = dessen Dateiname)."""
    import json
    main = metas[-1]
    for meta in metas[:-1]:
        path = kind_dir(meta["kind"]) / (meta["file"] + ".json")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["extra"].pop("part_of_user", None)
        data["extra"]["part_of"] = main["file"]
        tmp = path.with_name(path.name + ".part")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)


def discard(metas: list[dict]) -> None:
    """Pakete eines Auftrags samt Begleitdatei weg – auch halb geschriebene (.part) nach einem harten Abbruch."""
    for meta in metas:
        base = kind_dir(meta["kind"]) / meta["file"]
        for suffix in ("", ".part", ".json", ".json.part"):
            base.with_name(base.name + suffix).unlink(missing_ok=True)


__all__ = ["VerifyError", "bundles", "discard", "measure", "pack_all"]
