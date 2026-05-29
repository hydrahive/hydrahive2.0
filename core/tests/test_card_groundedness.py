from hydrahive.db._mirror_cards_model import derive_groundedness, Card, CARD_SCHEMA_VERSION


def test_observed_when_tool_results_dominate():
    assert derive_groundedness(tool_result_count=10, assistant_text_count=2) == "observed"


def test_claimed_when_assistant_text_dominates():
    assert derive_groundedness(tool_result_count=1, assistant_text_count=10) == "claimed"


def test_mixed_when_balanced():
    assert derive_groundedness(tool_result_count=5, assistant_text_count=4) == "mixed"


def test_empty_session_is_mixed():
    assert derive_groundedness(0, 0) == "mixed"


def test_card_defaults_v2_fields_unused():
    c = Card(card_id="card:s1", session_id="s1", gist="g", valence="good",
             salience="high", groundedness="observed")
    assert c.confidence == 1.0 and c.superseded_by == [] and c.schema_version == CARD_SCHEMA_VERSION
