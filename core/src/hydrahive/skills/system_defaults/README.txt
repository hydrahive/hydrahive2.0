Mitgelieferte System-Skills (werden nach $HH_DATA_DIR/skills/system/ installiert).

Beim Start aktualisiert HydraHive eine installierte Datei nur, wenn sie noch
genau einer früheren Auslieferung entspricht (SHA-256 in _history.json).
Hat ein Admin sie geändert, bleibt sie stehen (Warnung im Log).
Spec: docs/specs/system-skills-update.md

Nach JEDER Änderung an einer .md-Datei hier:
    python3 scripts/update_skill_history.py
und _history.json mit committen. Sonst schlägt
core/tests/test_system_skills_update.py fehl und die Änderung würde auf
bestehenden Installationen nie ankommen.
