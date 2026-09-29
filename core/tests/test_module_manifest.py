def test_parse_valid_manifest(tmp_path):
    import json
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"id": "example", "name": "Beispiel", "version": "1.0.0"}))
    from hydrahive.modules.manifest import ModuleManifest
    m = ModuleManifest.load(p)
    assert m.id == "example" and m.version == "1.0.0" and m.has_service is False


def test_manifest_rejects_bad_id(tmp_path):
    import json, pytest
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"id": "Bad Id!", "name": "x", "version": "1"}))
    from hydrahive.modules.manifest import ModuleManifest, ManifestError
    with pytest.raises(ManifestError):
        ModuleManifest.load(p)


def test_manifest_accepts_relative_persistent_globs(tmp_path):
    import json
    from hydrahive.modules.manifest import ModuleManifest

    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "id": "example",
        "name": "Example",
        "version": "1.0.0",
        "persistent_paths": ["*.mp3", "data/**/*.sqlite3"],
    }))

    assert ModuleManifest.load(p).persistent_paths == ("*.mp3", "data/**/*.sqlite3")


def test_manifest_defaults_persistent_paths_to_empty_tuple(tmp_path):
    import json
    from hydrahive.modules.manifest import ModuleManifest

    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"id": "example", "name": "Example", "version": "1.0.0"}))

    assert ModuleManifest.load(p).persistent_paths == ()


def test_manifest_rejects_invalid_persistent_globs(tmp_path):
    import json
    import pytest
    from hydrahive.modules.manifest import ManifestError, ModuleManifest

    invalid_values = [
        "*.mp3",
        None,
        [""],
        ["/var/lib/song.mp3"],
        ["../song.mp3"],
        ["audio/../../song.mp3"],
        ["./song.mp3"],
        [r"audio\*.mp3"],
        ["C:/audio/*.mp3"],
        [123],
    ]
    for persistent_paths in invalid_values:
        p = tmp_path / "manifest.json"
        p.write_text(json.dumps({
            "id": "example",
            "name": "Example",
            "version": "1.0.0",
            "persistent_paths": persistent_paths,
        }))
        with pytest.raises(ManifestError, match="persistent_paths"):
            ModuleManifest.load(p)


def _write(tmp_path, extra):
    import json
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"id": "demo", "name": "Demo", "version": "1.0.0", **extra}))
    return p


def test_manifest_capabilities_default_empty(tmp_path):
    from hydrahive.modules.manifest import ModuleManifest
    assert ModuleManifest.load(_write(tmp_path, {})).capabilities == ()


def test_manifest_parses_capabilities(tmp_path):
    from hydrahive.modules.manifest import ModuleManifest
    m = ModuleManifest.load(_write(tmp_path, {"capabilities": [
        {"id": "module.demo", "label": "Demo nutzen", "default": "everyone"},
        {"id": "demo.control", "label": "Steuern", "default": "admin_only", "tools": ["demo_do"]},
    ]}))
    assert [c.id for c in m.capabilities] == ["module.demo", "demo.control"]
    assert m.capabilities[1].default == "admin_only"
    assert m.capabilities[1].tools == ("demo_do",)
    assert m.capabilities[0].tools == ()


def test_manifest_rejects_foreign_capability_prefix(tmp_path):
    import pytest
    from hydrahive.modules.manifest import ManifestError, ModuleManifest
    for bad in ("module.other", "other.control", "core.vms", "demo", "demo.", "demo.Bad Name"):
        with pytest.raises(ManifestError):
            ModuleManifest.load(_write(tmp_path, {"capabilities": [{"id": bad, "label": "x"}]}))


def test_manifest_rejects_invalid_capability_default(tmp_path):
    import pytest
    from hydrahive.modules.manifest import ManifestError, ModuleManifest
    with pytest.raises(ManifestError):
        ModuleManifest.load(_write(tmp_path, {"capabilities": [
            {"id": "module.demo", "label": "x", "default": "nobody"}]}))


def test_manifest_rejects_duplicate_capability(tmp_path):
    import pytest
    from hydrahive.modules.manifest import ManifestError, ModuleManifest
    with pytest.raises(ManifestError):
        ModuleManifest.load(_write(tmp_path, {"capabilities": [
            {"id": "demo.x", "label": "a"}, {"id": "demo.x", "label": "b"}]}))


def test_manifest_capability_default_is_everyone(tmp_path):
    from hydrahive.modules.manifest import ModuleManifest
    m = ModuleManifest.load(_write(tmp_path, {"capabilities": [{"id": "demo.x", "label": "a"}]}))
    assert m.capabilities[0].default == "everyone"


def test_manifest_still_accepts_legacy_permissions(tmp_path):
    from hydrahive.modules.manifest import ModuleManifest
    m = ModuleManifest.load(_write(tmp_path, {"permissions": ["demo.read"]}))
    assert m.permissions == ("demo.read",) and m.capabilities == ()
