from hydrahive.db.connection import db


def test_apply_module_migrations_creates_and_tracks(mod_env):
    mdir = mod_env / "m"; mdir.mkdir()
    (mdir / "001_x.sql").write_text("CREATE TABLE module_x_t (id INTEGER);")
    from hydrahive.modules.migrations import apply_module_migrations
    apply_module_migrations("x", mdir)
    with db() as c:
        ver = c.execute("SELECT MAX(version) FROM module_schema_version WHERE module_id='x'").fetchone()[0]
        cols = [r[1] for r in c.execute("PRAGMA table_info(module_x_t)").fetchall()]
    assert ver == 1 and "id" in cols


def test_apply_module_migrations_idempotent_preserves_data(mod_env):
    mdir = mod_env / "m"; mdir.mkdir()
    (mdir / "001_y.sql").write_text("CREATE TABLE module_y_t (id INTEGER);")
    from hydrahive.modules.migrations import apply_module_migrations
    apply_module_migrations("y", mdir)
    with db() as c:
        c.execute("INSERT INTO module_y_t (id) VALUES (42)")
    apply_module_migrations("y", mdir)  # zweiter Lauf = Re-Install
    with db() as c:
        rows = c.execute("SELECT id FROM module_y_t").fetchall()
    assert [tuple(r) for r in rows] == [(42,)]  # Daten überleben
