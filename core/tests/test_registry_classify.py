def test_classify_chat_default():
    from hydrahive.llm.registry import _classify_catalog_entry
    assert _classify_catalog_entry({"id": "openrouter/foo", "output_modalities": [], "input_modalities": []}) == frozenset({"chat"})

def test_classify_image_and_music_from_output_modalities():
    from hydrahive.llm.registry import _classify_catalog_entry
    assert "image" in _classify_catalog_entry({"id": "x", "output_modalities": ["image"]})
    assert "music" in _classify_catalog_entry({"id": "x", "output_modalities": ["audio"]})

def test_classify_unknown_is_chat():
    from hydrahive.llm.registry import _classify_catalog_entry
    assert _classify_catalog_entry({"id": "nvidia_nim/foo"}) == frozenset({"chat"})
