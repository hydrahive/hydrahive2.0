---
name: test
description: Generiert Unit-Tests, Integrations-Tests und Test-Daten. Für das Schreiben von Tests, Verbesserung der Test-Coverage oder Erstellung von Edge-Case-Szenarien.
when_to_use: Wenn Tests für neuen Code geschrieben werden sollen, Coverage verbessert werden soll, oder Edge Cases und Fixtures gebraucht werden.
tools_required: [file_read, file_write, shell_exec]
---

# Test-Generierungs-Skill

> Abschnitte 0 und 8 nach „test-driven-development“ / „writing-good-tests“ aus Superpowers v7.0.2 (github.com/obra/superpowers, MIT, © 2025 Jesse Vincent – Lizenztext: docs/third-party/superpowers-LICENSE).

## 0. Zuerst der rote Test

Neue Funktion oder Fix: **erst der Test, dann der Code.** Den Test laufen lassen und **rot** sehen – sonst testest du das Falsche. Dann minimal umsetzen, grün sehen, aufräumen, committen.

*HydraHive-Abweichung vom Original* (dort: Code vor dem Test → löschen und neu anfangen): Wird ein Test erst nachträglich geschrieben, Fix kurz zurücknehmen, Test muss rot werden, Fix wieder rein. Erst diese Gegenprobe macht ihn zum Regressionstest.

**„Grün“ heißt die Suite des Projekts, nicht nur deine Datei.** Lokal laufen nur die gezielten Tests der betroffenen Bereiche (die Platte ist langsam, keine lokale Vollsuite) – maßgeblich ist danach die **komplette CI des PRs**. Jeder rote Test dort gehört mit Namen in den Bericht, auch einer, den du nicht verursacht hast. Ein roter Test, den du gesehen und nicht erwähnt hast, macht den Bericht falsch.

Befehl im Kern: `cd core && PYTHONPATH=src pytest -q tests/test_<bereich>*.py` (parallel: `-n 4`).

## 1. Unit Tests — Python (pytest)

```python
import pytest
from mymodule import my_function

class TestMyFunction:
    def test_normal_case(self):
        assert my_function("input") == "expected"

    def test_empty_input(self):
        assert my_function("") == ""

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            my_function(None)

    @pytest.mark.parametrize("input,expected", [
        ("a", "A"),
        ("hello", "HELLO"),
    ])
    def test_parametrized(self, input, expected):
        assert my_function(input) == expected
```

## 2. FastAPI Integrations-Tests

```python
import pytest
from fastapi.testclient import TestClient
from myapp.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_create_resource(client):
    r = client.post("/api/resource", json={"name": "test"})
    assert r.status_code == 201
    assert r.json()["name"] == "test"

def test_not_found(client):
    r = client.get("/api/resource/99999")
    assert r.status_code == 404
```

## 3. SQLite-Fixtures (HH2-Style)

```python
import pytest
import sqlite3

@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(open("migrations/001_init.sql").read())
    yield conn
    conn.close()

def test_insert_and_query(db):
    db.execute("INSERT INTO sessions (id, agent_id) VALUES (?, ?)", ("s1", "a1"))
    row = db.execute("SELECT * FROM sessions WHERE id = ?", ("s1",)).fetchone()
    assert row["agent_id"] == "a1"
```

## 4. Attrappen – nur für das Langsame oder Externe

Nur ersetzen, was langsam oder extern ist (Netz, LLM, `systemctl`, fremde Dienste). Geprüft wird **das Verhalten deines Codes** mit der Attrappe – nicht die Attrappe selbst (siehe Abschnitt 8).

```python
from unittest.mock import patch

def test_holt_kurs_und_rundet_auf_zwei_stellen():
    # extern: die Kurs-API; echt: unsere Umrechnung und Rundung
    with patch("hydrahive.mymodule._fetch_price", return_value={"eur": 41234.5678}):
        assert format_price("bitcoin") == "41.234,57 €"

def test_api_fehler_ergibt_klare_meldung_statt_absturz():
    with patch("hydrahive.mymodule._fetch_price", side_effect=TimeoutError):
        assert format_price("bitcoin") == "Kurs gerade nicht erreichbar"
```

Nicht so: `mock.assert_called_once()` als einzige Prüfung, oder den Rückgabewert der Attrappe wieder zurück-prüfen (`assert result["data"] == "mocked"`) – das beweist nur, dass die Attrappe da ist. Ist der Aufruf selbst Teil des Vertrags (Argumente, Anzahl, Reihenfolge), ihn **zusätzlich** zum Ergebnis prüfen.

## 5. Coverage prüfen

```bash
pytest --cov=hydrahive --cov-report=html tests/
open htmlcov/index.html
```

## 6. Test-Kategorien

Für jede Funktion Tests schreiben für:
- **Happy Path** — normaler erwarteter Input
- **Edge Cases** — leer, null, Maxlänge
- **Error Cases** — ungültige Typen, fehlende Pflichtfelder
- **Boundary Conditions** — Off-by-one, Limits
- **Auth** — nicht authentifiziert, falsche Permissions
- **Async** — mehrere parallele Aufrufe

## 7. Was einen guten Test ausmacht

- Eine Assertion pro Test (oder eng verwandte)
- Testname beschreibt das Szenario: `test_create_session_returns_201`
- Keine Logik in Tests — deterministischer Input, deterministisches Assert
- Isoliert — kein Shared State zwischen Tests
- Schnell — nur Langsames/Externes ersetzen (Netz, LLM, Dienste), echte SQLite im tmp-Pfad statt Attrappe

## 8. Jeder Test fängt einen bestimmten Fehler

**Nenne den Fehler, bevor du den Test schreibst:** Welche Änderung am Produktivcode soll ihn rot machen – und ist das ein Fehler oder eine bewusste Entscheidung?

- **Erwartung unabhängig herleiten:** Literale und von Hand geprüfte Daten. Eine Erwartung, die der getestete Code selbst (oder seine Helfer) berechnet, ist immer wahr.
  ```python
  # falsch: beide Seiten aus demselben Builder – immer gleich
  assert build_query(tag="urgent") == build_query(tag="urgent")
  # richtig: von Hand
  assert build_query(tag="urgent") == 'tag:"urgent"'
  ```
- **Keine Änderungsmelder:** Ein Test, der nur bei bewussten Entscheidungen rot wird (Konstante, genauer Meldungstext, private Struktur), schlägt bei jedem Umbau an und verschläft Fehler. Teste das Verhalten, das an der Entscheidung hängt: nicht `assert MAX_RETRIES == 5`, sondern „ein fehlschlagender Aufruf wird 5-mal wiederholt, ein 6. Versuch passiert nie“.
- **Verhalten statt Text:** Dass ein Skript oder eine Konfiguration eine bestimmte Zeile enthält, beweist nur, dass die Datei die Datei ist. Skripte mit kontrollierten Eingaben laufen lassen (Attrappen für `systemctl`, `curl` wie in `tests/_update_fakes.py`) und Ausgabe, Seiteneffekte, Exit-Code prüfen. Strukturtests auf Text nur als Wächter gegen Rückfälle, nicht als einziger Beweis.
- **Dein Code, nicht das Framework:** Teste den Vertrag an deinen Grenzen (Route, Abfrage, Antwort), nicht die Mechanik von FastAPI oder SQLite.

**Echtes testen, nicht die Attrappe:**
- Eine Zusicherung auf eine Attrappe beweist nur, dass die Attrappe da ist. „Testen wir gerade das Verhalten eines Mocks?“
- Auf der richtigen Ebene ersetzen: erst die Seiteneffekte der echten Methode kennen, nur das Langsame oder Externe ersetzen, den Rest echt lassen.
- Attrappen spiegeln die echte Struktur vollständig (alle Felder), sonst bricht die Integration still.
- Aufräum-Methoden, die nur Tests brauchen, gehören in Test-Helfer, nicht in die Produktivklasse. Aufräumen nur eigener Zeilen: `tests/_own_rows.py`.
- Wird der Mock-Aufbau größer als der Test: Integrationstest mit echten Teilen.

**Mutations-Check vor dem Abschluss** – gedanklich den Code verändern; für jede realistische Änderung muss mindestens ein Test rot werden: falsche Konstante/Argument, falscher Zweig, fehlende Zustandsänderung oder Seiteneffekt, leere/Standard-Rückgabe, fehlende Prüfung für 0, leer, None, unberechtigt, kaputte Eingabe. Fängt nichts eine Änderung, ist das Verhalten ungeschützt – oder der Test tautologisch.

**Warnzeichen:** Aufbau und Zusicherung nutzen dasselbe Objekt · Test kann nur durch Absturz rot werden · Erwartungen hinter Schleifen/Helfern versteckt · Test existiert nur für die Abdeckung · Attrappen-Aufbau ist mehr als der halbe Test · „sicherheitshalber gemockt“ · Test hängt von Daten anderer Tests in derselben DB ab (Budget aus den tatsächlich vorhandenen Daten ableiten).
