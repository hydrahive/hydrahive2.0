"""Frontend-Vertrag für optionale Media-Widgets im Buddy-Cockpit."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_module_generator_collects_dedicated_buddy_media_widgets():
    source = (ROOT / "frontend/scripts/gen-modules.mjs").read_text()

    assert 'moduleBuddyMediaWidgets' in source
    assert '_opt(m, "buddyMediaWidgets")' in source


def test_buddy_consumes_only_the_dedicated_media_widget_export():
    source = (ROOT / "frontend/src/features/buddy/BuddyPage.tsx").read_text()

    assert "moduleBuddyMediaWidgets" in source
    assert "normalizeBuddyMediaWidgets" in source
    assert "BUDDY_MEDIA_WIDGETS.map" in source


def test_media_widget_normalizer_has_stable_validation_and_ordering():
    source = (ROOT / "frontend/src/features/buddy/moduleMediaWidgets.ts").read_text()

    assert "isBuddyMediaWidget" in source
    assert "seen.has" in source
    assert "order -" in source
    assert "localeCompare" in source


def test_buddy_rendert_keine_modul_widgets():
    """Die alten Modul-Kacheln (Gesundheit, Aufgaben …) bleiben draußen.

    35627cdc hat sie bewusst entfernt — sie schicken fast nur Prompts. Nicht als
    Regression "reparieren" (das war c5a8303d und wurde zurückgenommen).
    """
    page = (ROOT / "frontend/src/features/buddy/BuddyPage.tsx").read_text()
    assert "moduleBuddyWidgets" not in page
    assert "BuddyModuleWidgets" not in page
    assert not (ROOT / "frontend/src/features/buddy/_BuddyModuleWidgets.tsx").exists()


def test_buddy_zeigt_zahnfee_briefing_wieder():
    """Regression d041b2cf: das Morgen-Briefing war im Buddy nirgends mehr sichtbar (MED-4)."""
    page = (ROOT / "frontend/src/features/buddy/BuddyPage.tsx").read_text()
    box = (ROOT / "frontend/src/features/buddy/_BuddyBriefingBox.tsx").read_text()
    assert "BuddyBriefingBox" in page
    # Die Box sitzt in der LINKEN Leiste (unter dem Buddy-Panel), nicht rechts.
    left = page[page.index("function BuddyLeftRail("):page.index("function BuddyRightRail(")]
    right = page[page.index("function BuddyRightRail("):]
    assert "<BuddyBriefingBox" in left and "<BuddyBriefingBox" not in right
    assert "zahnfeeApi.briefing()" in box
    assert not (ROOT / "frontend/src/features/buddy/_BuddyLeftPanel.tsx").exists()
