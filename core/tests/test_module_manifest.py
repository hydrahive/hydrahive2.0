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
