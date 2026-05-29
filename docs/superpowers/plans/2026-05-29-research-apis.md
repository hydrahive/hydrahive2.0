# Forschungs-APIs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kuratierte Registry wissenschaftlich/medizinischer Research-APIs, die Agenten per `fetch_url` nutzen — Keys verschlüsselt + transparent injiziert, How-to als Skill, Config-UI im Health-Bereich.

**Architecture:** Backend-Registry (`research/`) mit verschlüsselter Persistenz (`/etc/hydrahive2/research_apis.json`); `fetch_url` bekommt die Registry als **zweite** Auth-Quelle (nach dem per-User-Credential-Store); Admin-Route fürs CRUD; ein `system_defaults`-Skill liefert das How-to; Frontend-View in `features/health/`. **Kein** Wrapper-Tool pro API.

**Tech Stack:** Python 3.12, pytest, bestehende `credentials._crypto` (AES-GCM), React/Vite (Frontend), kein neuer Dependency.

**SPEC:** `SPEC.md` → „Forschungs-APIs — … (Core-Komponente)" (Commit `95de42c`).

---

## File Structure

- Create: `core/src/hydrahive/research/__init__.py` — Public-API (Re-Exports: `match_research_api`, store-Funktionen).
- Create: `core/src/hydrahive/research/models.py` — `ResearchApi`-Dataclass + Validierung.
- Create: `core/src/hydrahive/research/_seed.py` — vorbefüllte Quellen-Liste (~14 APIs).
- Create: `core/src/hydrahive/research/store.py` — verschlüsselte Persistenz + seed-merge + `match_research_api`.
- Modify: `core/src/hydrahive/settings/_paths.py` — `research_apis_config`-Pfad.
- Modify: `core/src/hydrahive/tools/fetch_url.py` — Registry als zweite Auth-Quelle.
- Create: `core/src/hydrahive/api/routes/research_apis.py` — Admin-CRUD + Test.
- Modify: `core/src/hydrahive/api/main.py` — Router registrieren.
- Create: `core/src/hydrahive/skills/system_defaults/medical-research.md` — How-to-Skill.
- Create: `frontend/src/features/health/ResearchApisView.tsx` — Config-UI.
- Modify: `frontend/src/features/health/api.ts` — `researchApi`-Client.
- Modify: `frontend/src/features/health/HealthSidebar.tsx` + `HealthPage.tsx` — Nav + Route.
- Test: `core/tests/test_research_apis.py` (neu).

---

### Task 0: Branch + Pfad

- [ ] **Step 1: Branch**

```bash
cd /home/till/hydrahive2.0 && git checkout main && git pull --ff-only
git checkout -b feat/research-apis
```

- [ ] **Step 2: Config-Pfad ergänzen** in `core/src/hydrahive/settings/_paths.py` (nach `api_keys_config`):

```python
    @cached_property
    def research_apis_config(self) -> Path:
        return self.config_dir / "research_apis.json"
```

- [ ] **Step 3: Smoke** — `cd core && ~/.venv-cards/bin/python -c "from hydrahive.settings import settings; print(settings.research_apis_config)"` → `/etc/hydrahive2/research_apis.json` (oder dev-Pfad).

---

### Task 1: Model + Seed (mit Endpoint-Verifikation)

**Files:** Create `core/src/hydrahive/research/models.py`, `research/_seed.py`, `research/__init__.py`; Test `core/tests/test_research_apis.py`.

- [ ] **Step 1: Endpoints/Auth via context7 + offizielle Docs verifizieren** (CLAUDE.md-Regel: APIs ändern sich — nicht aus dem Gedächtnis seeden). Für jede Quelle base_url + Auth-Mechanismus prüfen (PubMed E-utilities `api_key`-Query, OpenAlex `mailto`-Query, Crossref `mailto`, Semantic Scholar `x-api-key`-Header, CORE `Authorization: Bearer`, openFDA `api_key`-Query, ClinicalTrials.gov v2, OpenAlex/MyGene/HPO/Open Targets keyless, ICD-11 = OAuth-Client-Credentials → in v1 disabled seeden). Ergebnisse in den Seed eintragen.

- [ ] **Step 2: Failing test** (`core/tests/test_research_apis.py`):

```python
from hydrahive.research.models import ResearchApi, AUTH_TYPES, CATEGORIES
from hydrahive.research._seed import SEED


def test_seed_integrity():
    ids = [a.id for a in SEED]
    assert len(ids) == len(set(ids))                      # eindeutige ids
    assert len(SEED) >= 12
    for a in SEED:
        assert a.id and a.base_url and a.name
        assert a.category in CATEGORIES
        assert a.auth_type in AUTH_TYPES
        if a.needs_key:
            assert a.auth_param or a.auth_type == "bearer"  # wohin der Key geht
        else:
            assert a.enabled                                # keyless ist default aktiv


def test_keyless_pubmed_and_openalex_present():
    by_id = {a.id: a for a in SEED}
    assert by_id["pubmed"].base_url.startswith("https://")
    assert by_id["openalex"].polite_email_param == "mailto"
```

- [ ] **Step 3: Test → FAIL** (`research` existiert nicht).

Run: `cd /home/till/hydrahive2.0/core && ~/.venv-cards/bin/python -m pytest tests/test_research_apis.py -q`

- [ ] **Step 4: Model implementieren** (`research/models.py`):

```python
from __future__ import annotations

from dataclasses import dataclass, field

CATEGORIES = ("literatur", "medikamente", "krankheiten_gene", "studien")
AUTH_TYPES = ("none", "query", "header", "bearer")


@dataclass
class ResearchApi:
    id: str
    name: str
    category: str
    base_url: str
    url_pattern: str                 # für fetch_url-Matching (z.B. https://api.fda.gov/*)
    docs_url: str = ""
    description: str = ""
    needs_key: bool = False
    auth_type: str = "none"          # none|query|header|bearer
    auth_param: str = ""             # Query-Param- bzw. Header-Name (bei bearer leer)
    polite_email_param: str = ""     # z.B. "mailto" (OpenAlex/Crossref) — kein Secret
    rate_limit: str = ""
    enabled: bool = True
    key: str = ""                    # Secret; in der Registry verschlüsselt

    def public_dict(self) -> dict:
        """Ohne Klartext-Key — fürs Frontend/GET (nur has_key-Flag)."""
        d = {k: getattr(self, k) for k in (
            "id", "name", "category", "base_url", "url_pattern", "docs_url",
            "description", "needs_key", "auth_type", "auth_param",
            "polite_email_param", "rate_limit", "enabled")}
        d["has_key"] = bool(self.key)
        return d
```

- [ ] **Step 5: Seed implementieren** (`research/_seed.py`) — die in Step 1 verifizierten Quellen, z.B.:

```python
from hydrahive.research.models import ResearchApi

SEED: list[ResearchApi] = [
    ResearchApi(id="pubmed", name="PubMed / NCBI E-utilities", category="literatur",
                base_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
                url_pattern="https://eutils.ncbi.nlm.nih.gov/*",
                docs_url="https://www.ncbi.nlm.nih.gov/books/NBK25501/",
                description="36 Mio+ med. Abstracts. Standard.",
                needs_key=False, auth_type="query", auth_param="api_key",
                rate_limit="3/s ohne Key, 10/s mit Key", enabled=True),
    ResearchApi(id="europepmc", name="Europe PMC", category="literatur",
                base_url="https://www.ebi.ac.uk/europepmc/webservices/rest/",
                url_pattern="https://www.ebi.ac.uk/europepmc/*",
                description="Wie PubMed, oft mit Volltext.", enabled=True),
    ResearchApi(id="openalex", name="OpenAlex", category="literatur",
                base_url="https://api.openalex.org/",
                url_pattern="https://api.openalex.org/*",
                description="Offener Wissenschafts-Katalog. Polite-Pool via mailto.",
                polite_email_param="mailto", enabled=True),
    # … Semantic Scholar (header x-api-key, optional), Crossref (mailto), CORE
    #    (bearer, needs_key), bioRxiv/medRxiv, openFDA (query api_key, optional),
    #    RxNorm, MyGene, MyVariant, Open Targets (GraphQL), HPO,
    #    ClinicalTrials.gov v2 — alle aus Step 1 verifiziert.
    # ICD-11 (WHO): OAuth-Client-Credentials → in v1 enabled=False + docs_url-Hinweis.
]
```

- [ ] **Step 6: `__init__.py`** Re-Exports (zunächst leer/Model):

```python
from hydrahive.research.models import ResearchApi  # noqa: F401
```

- [ ] **Step 7: Test → PASS.** Run wie Step 3.

- [ ] **Step 8: Commit**

```bash
git add core/src/hydrahive/research/ core/tests/test_research_apis.py
git commit -m "feat(research): ResearchApi-Model + verifizierter Seed der Quellen

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Verschlüsselter Store + seed-merge

**Files:** Create `research/store.py`; Modify `research/__init__.py`; Test erweitern.

- [ ] **Step 1: Failing tests** (anhängen):

```python
def test_store_roundtrip_and_seed_merge(tmp_path, monkeypatch):
    import hydrahive.research.store as st
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "research_apis_config", tmp_path / "research_apis.json", raising=False)
    monkeypatch.setattr(settings, "_data_dir", tmp_path, raising=False)  # für encrypt-Key

    # frischer Store = Seed
    apis = {a.id: a for a in st.list_apis()}
    assert "pubmed" in apis and apis["pubmed"].enabled

    # Key setzen + enabled togglen → persistiert + verschlüsselt auf Platte
    st.set_key("core", "SECRET123")
    st.set_enabled("core", True)
    raw = (tmp_path / "research_apis.json").read_text()
    assert "SECRET123" not in raw                 # Key NICHT im Klartext
    assert st.get_api("core").key == "SECRET123"  # entschlüsselt geladen


def test_public_list_masks_key(monkeypatch, tmp_path):
    import hydrahive.research.store as st
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "research_apis_config", tmp_path / "r.json", raising=False)
    monkeypatch.setattr(settings, "_data_dir", tmp_path, raising=False)
    st.set_key("core", "X")
    pub = {a["id"]: a for a in st.list_public()}
    assert pub["core"]["has_key"] is True and "key" not in pub["core"]
```

- [ ] **Step 2: Test → FAIL.**

- [ ] **Step 3: Store implementieren** (`research/store.py`) — Persistenz = nur die **Overrides** (key/enabled/polite_email pro id); beim Laden über den Seed gemergt (neue Seed-Einträge erscheinen automatisch, Admin-Edits bleiben):

```python
from __future__ import annotations

import json
import logging
import os

from hydrahive.credentials._crypto import decrypt, encrypt
from hydrahive.research._seed import SEED
from hydrahive.research.models import ResearchApi
from hydrahive.settings import settings

logger = logging.getLogger(__name__)
_OVERRIDE_FIELDS = ("key", "enabled", "polite_email", "auth_param")


def _load_overrides() -> dict:
    path = settings.research_apis_config
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError:
        logger.warning("Defekte research_apis.json: %s", path)
        return {}
    for ov in raw.values():
        if isinstance(ov, dict) and ov.get("key"):
            ov["key"] = decrypt(ov["key"], settings.data_dir)
    return raw


def _save_overrides(overrides: dict) -> None:
    path = settings.research_apis_config
    path.parent.mkdir(parents=True, exist_ok=True)
    enc = {
        rid: {**ov, "key": encrypt(ov["key"], settings.data_dir)} if ov.get("key") else ov
        for rid, ov in overrides.items()
    }
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(enc, indent=2, ensure_ascii=False))
    tmp.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def list_apis() -> list[ResearchApi]:
    overrides = _load_overrides()
    out = []
    for base in SEED:
        ov = overrides.get(base.id, {})
        out.append(ResearchApi(**{**base.__dict__, **{
            k: ov[k] for k in _OVERRIDE_FIELDS if k in ov}}))
    return out


def get_api(rid: str) -> ResearchApi | None:
    return next((a for a in list_apis() if a.id == rid), None)


def list_public() -> list[dict]:
    return [a.public_dict() for a in list_apis()]


def _set_override(rid: str, **fields) -> bool:
    if not any(s.id == rid for s in SEED):
        return False
    overrides = _load_overrides()
    overrides.setdefault(rid, {}).update(fields)
    _save_overrides(overrides)
    return True


def set_key(rid: str, key: str) -> bool:
    return _set_override(rid, key=key)


def set_enabled(rid: str, enabled: bool) -> bool:
    return _set_override(rid, enabled=enabled)
```

- [ ] **Step 4: `__init__.py`** erweitern: `from hydrahive.research.store import list_apis, list_public, get_api, set_key, set_enabled  # noqa: F401`

- [ ] **Step 5: Test → PASS.**

- [ ] **Step 6: Commit** (`feat(research): verschlüsselter Store + seed-merge`).

---

### Task 3: `fetch_url` — Registry als zweite Auth-Quelle

**Files:** Modify `tools/fetch_url.py`, `research/store.py` (+ `match_research_api`); Test erweitern.

- [ ] **Step 1: Failing test** (`match_research_api` liefert ein injizierbares Credential-Äquivalent):

```python
def test_match_research_api_injects_for_keyed(monkeypatch, tmp_path):
    import hydrahive.research.store as st
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "research_apis_config", tmp_path / "r.json", raising=False)
    monkeypatch.setattr(settings, "_data_dir", tmp_path, raising=False)
    st.set_key("core", "K"); st.set_enabled("core", True)
    cred = st.match_research_api("https://api.core.ac.uk/v3/search/works?q=x")
    assert cred is not None and cred.value == "K" and cred.type == "bearer"


def test_match_research_api_none_for_keyless_or_disabled(monkeypatch, tmp_path):
    import hydrahive.research.store as st
    from hydrahive.settings import settings
    monkeypatch.setattr(settings, "research_apis_config", tmp_path / "r.json", raising=False)
    monkeypatch.setattr(settings, "_data_dir", tmp_path, raising=False)
    # keyless API → keine Injektion nötig
    assert st.match_research_api("https://api.openalex.org/works") is None
```

- [ ] **Step 2: Test → FAIL.**

- [ ] **Step 3: `match_research_api` implementieren** (`research/store.py`) — nutzt das bestehende `Credential`-Model + `matches_url`, damit `fetch_url._apply_auth` es unverändert verarbeitet:

```python
def match_research_api(url: str):
    """Erst-passende aktivierte, keyed Registry-API → Credential-Äquivalent (oder None).
    Keyless APIs brauchen keine Injektion → None."""
    from hydrahive.credentials.models import Credential, matches_url
    for a in list_apis():
        if not (a.enabled and a.needs_key and a.key):
            continue
        if not matches_url(a.url_pattern, url):
            continue
        ctype = {"query": "query", "header": "header", "bearer": "bearer"}.get(a.auth_type)
        if not ctype:
            continue
        return Credential(
            name=f"research:{a.id}", type=ctype, value=a.key,
            url_pattern=a.url_pattern,
            header_name=a.auth_param if a.auth_type == "header" else "",
            query_param=a.auth_param if a.auth_type == "query" else "",
        )
    return None
```

`__init__.py`: `match_research_api` mit re-exportieren.

- [ ] **Step 4: `fetch_url._execute` erweitern** (Z. ~152) — per-User-Credential hat Vorrang, Registry ist Fallback:

```python
    cred = match_credential(ctx.user_id, url, prefer_name=auth_name)
    if not cred and not auth_name:
        from hydrahive.research import match_research_api
        cred = match_research_api(url)
    if cred:
        auth_used = _apply_auth(cred, headers, params)
```

- [ ] **Step 5: Test (inkl. fetch_url-Smoke) → PASS.** Volle cards/research-Tests grün.

- [ ] **Step 6: Commit** (`feat(research): fetch_url nutzt Registry als zweite Auth-Quelle`).

---

### Task 4: Admin-Route

**Files:** Create `api/routes/research_apis.py`; Modify `api/main.py`; Test erweitern.

- [ ] **Step 1: Failing test** (require_admin + Maskierung + PATCH). Muster aus bestehenden Route-Tests (TestClient, Admin-Auth-Fixture) übernehmen — vorher `grep -rl "require_admin" core/tests` für das vorhandene Auth-Fixture-Muster.

- [ ] **Step 2: Test → FAIL.**

- [ ] **Step 3: Route implementieren** (`api/routes/research_apis.py`) nach dem `llm.py`-Muster:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from hydrahive.api.deps import require_admin   # gleiche Quelle wie llm.py nutzt
from hydrahive import research

router = APIRouter(prefix="/api/research-apis", tags=["research-apis"])


class ApiUpdate(BaseModel):
    enabled: bool | None = None
    key: str | None = None


@router.get("")
async def list_apis(_=Depends(require_admin)):
    return {"apis": research.list_public()}


@router.patch("/{rid}")
async def update_api(rid: str, body: ApiUpdate, _=Depends(require_admin)):
    if research.get_api(rid) is None:
        raise HTTPException(404, "unknown api")
    if body.enabled is not None:
        research.set_enabled(rid, body.enabled)
    if body.key is not None:
        research.set_key(rid, body.key)
    return research.get_api(rid).public_dict()


@router.post("/{rid}/test")
async def test_api(rid: str, _=Depends(require_admin)):
    """Health-Check: GET auf base_url (mit Key-Injektion via fetch_url-Logik)."""
    a = research.get_api(rid)
    if a is None:
        raise HTTPException(404, "unknown api")
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
            r = await c.get(a.base_url)
        return {"ok": r.status_code < 500, "status": r.status_code}
    except httpx.HTTPError as e:
        return {"ok": False, "error": str(e)}
```

`api/main.py`: Router einhängen (Muster der anderen `include_router`).

- [ ] **Step 4: Test → PASS.**

- [ ] **Step 5: Commit** (`feat(research): Admin-Route /api/research-apis`).

---

### Task 5: `medical-research`-Skill

**Files:** Create `core/src/hydrahive/skills/system_defaults/medical-research.md`.

- [ ] **Step 1: Skill schreiben** — Frontmatter (`name: medical-research`, `description`, `when_to_use`, `tools_required: [fetch_url]`) + Body: pro Quelle 1 Block (wofür, base_url, Query-Syntax-Beispiel, „rufe via fetch_url auf"). Hinweis: keyless-Quellen bevorzugen; bei 401/403 ist der Key nicht konfiguriert. Endpoints/Syntax aus Task-1-Step-1-Verifikation.

- [ ] **Step 2: Test** (`test_research_apis.py`) — Skill parst + hat den Namen:

```python
def test_medical_research_skill_parses():
    from pathlib import Path
    from hydrahive.skills.models import parse
    p = Path("src/hydrahive/skills/system_defaults/medical-research.md")
    skill = parse(p.read_text(encoding="utf-8"), scope="system", owner="system", fallback_name="medical-research")
    assert skill.name == "medical-research" and skill.description
```

- [ ] **Step 3: Test → PASS** (run aus `core/`).

- [ ] **Step 4: Commit** (`feat(research): medical-research-Skill (How-to)`).

---

### Task 6: Frontend — Health-View

**Files:** Create `frontend/src/features/health/ResearchApisView.tsx`; Modify `features/health/api.ts`, `HealthSidebar.tsx`, `HealthPage.tsx`.

Vorlage: `features/llm/` (Config-Seite mit Karten + Speichern/Test). Frontend wird von Till im Browser verifiziert (CLAUDE.md: Till testet).

- [ ] **Step 1: API-Client** (`features/health/api.ts`) — `researchApi.list()` → `GET /api/research-apis`; `researchApi.update(id, {enabled?, key?})` → `PATCH`; `researchApi.test(id)` → `POST .../test`. Interface `ResearchApiPublic` (id, name, category, base_url, docs_url, needs_key, has_key, auth_type, enabled, rate_limit, polite_email_param).

- [ ] **Step 2: View** (`ResearchApisView.tsx`) — lädt die Liste, gruppiert nach `category` (Literatur / Medikamente / Krankheiten & Gene / Studien), Karte je API: Name + Beschreibung + docs-Link, Enabled-Toggle, Key-Feld nur wenn `needs_key` (Platzhalter „•••• gesetzt" wenn `has_key`), Test-Button (zeigt Status). Speichern ruft `researchApi.update`.

- [ ] **Step 3: Nav + Route** — `HealthSidebar.tsx`: Eintrag „Forschungs-APIs" (Route `/health/forschungs-apis`); `HealthPage.tsx`: Route → `<ResearchApisView />`.

- [ ] **Step 4: Build grün** — `cd frontend && npm run build` (tsc + vite) ohne Fehler.

- [ ] **Step 5: Commit** (`feat(research): Health-View Forschungs-APIs`).

---

### Task 7: Suite, Review, Merge, Deploy, Verifikation

- [ ] **Step 1: Volle Core-Suite** — `cd core && ~/.venv-cards/bin/python -m pytest -q` grün.
- [ ] **Step 2: Frontend-Build** — `cd frontend && npm run build` grün.
- [ ] **Step 3: code-reviewer-Agent** über den Branch-Diff (wie beim cards-Fix) — Findings fixen.
- [ ] **Step 4: Review durch Till** — Diff vorlegen, OK abwarten.
- [ ] **Step 5: Merge nach main** (kein PR) + push.
- [ ] **Step 6: Deploy `.22`** (Till) — `install_system_defaults` zieht den Skill, DDL/Pfade kommen beim Restart. Version via `hh_status` prüfen.
- [ ] **Step 7: Till verifiziert** im Browser: Health → Forschungs-APIs sichtbar, Toggle/Key/Test funktioniert; ein Agent kann mit dem `medical-research`-Skill via `fetch_url` z.B. PubMed abfragen. Optional: Playground anbieten.

---

## Self-Review

- **Spec-Coverage:** Registry (T1/T2) ✓, Key-Verwaltung verschlüsselt (T2) ✓, transparente Injektion (T3) ✓, Skill (T5) ✓, Health-UI (T6) ✓, keyless-default-aktiv (T1 seed) ✓, kein Wrapper-Tool (nur fetch_url) ✓. Nicht-Ziele eingehalten (kein Caching, keine DE-DB, kein Scraping).
- **Placeholder-Scan:** Backend-Code konkret; Seed-Details + Skill-Inhalt hängen an der **Endpoint-Verifikation** (T1/S1, T5/S1) — bewusst als Verifikations-Schritt statt geratenem Code (CLAUDE.md „verify before build"). Frontend referenziert das `features/llm/`-Muster konkret (Till testet UI).
- **Typ-Konsistenz:** `ResearchApi` (T1) → `store` (T2) → `match_research_api`→`Credential` (T3) → Route `public_dict` (T4) → Frontend-Interface (T6). `_OVERRIDE_FIELDS` deckt key/enabled/polite_email/auth_param.
- **Risiko:** `fetch_url`-Änderung ist additiv (per-User-Credential behält Vorrang; Registry nur Fallback, nur bei keyed+enabled). ICD-11-OAuth bewusst v1-disabled. `match_research_api` lädt pro Call die Registry — bei Bedarf später cachen (YAGNI).
