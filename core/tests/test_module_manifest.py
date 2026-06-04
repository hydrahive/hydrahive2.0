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
