from hydrahive.media_timeline_assembly import video_onair_segments, video_render_plan


def _tl(tracks, cut_points=None):
    return {"tracks": tracks, "cut_points": cut_points or []}


def test_single_track_no_cuts():
    tl = _tl([{"id": "vid1", "kind": "video", "clips": [{"id": "a", "start": 0, "duration": 10}]}])
    seg = video_onair_segments(tl)
    assert seg == {"a": [(0.0, 10.0)]}


def test_toggle_at_cut_point():
    # vid1 0-10, vid2 überlappt 4-14, Schnittpunkt bei 6.
    tl = _tl(
        [
            {"id": "vid1", "kind": "video", "clips": [{"id": "a", "start": 0, "duration": 10}]},
            {"id": "vid2", "kind": "video", "clips": [{"id": "b", "start": 4, "duration": 10}]},
        ],
        [{"id": "c", "time": 6}],
    )
    seg = video_onair_segments(tl)
    # Vor 6 → vid1 (a), ab 6 → vid2 (b).
    assert seg["a"] == [(0.0, 6.0)]
    assert seg["b"] == [(6.0, 14.0)]


def test_fallback_on_gap():
    # Aktive Spur vid1 hat Lücke ab 5, vid2 deckt 0-20 → Fallback auf b.
    tl = _tl(
        [
            {"id": "vid1", "kind": "video", "clips": [{"id": "a", "start": 0, "duration": 5}]},
            {"id": "vid2", "kind": "video", "clips": [{"id": "b", "start": 0, "duration": 20}]},
        ],
    )
    seg = video_onair_segments(tl)
    # 0-5 zeigt a (vid1 primär), 5-20 Fallback auf b.
    assert seg["a"] == [(0.0, 5.0)]
    assert seg["b"] == [(5.0, 20.0)]


def test_two_cuts_back_to_vid1():
    tl = _tl(
        [
            {"id": "vid1", "kind": "video", "clips": [{"id": "a", "start": 0, "duration": 20}]},
            {"id": "vid2", "kind": "video", "clips": [{"id": "b", "start": 0, "duration": 20}]},
        ],
        [{"id": "c1", "time": 5}, {"id": "c2", "time": 10}],
    )
    seg = video_onair_segments(tl)
    # 0-5 vid1, 5-10 vid2, 10-20 vid1 → a hat zwei Segmente, b eins.
    assert seg["a"] == [(0.0, 5.0), (10.0, 20.0)]
    assert seg["b"] == [(5.0, 10.0)]


def _ab_timeline(effect, duration, cut=6):
    return _tl(
        [
            {"id": "vid1", "kind": "video", "clips": [{"id": "a", "start": 0, "duration": 12}]},
            {"id": "vid2", "kind": "video", "clips": [{"id": "b", "start": 0, "duration": 12}]},
        ],
        [{"id": "c", "time": cut, "effect": effect, "duration": duration}],
    )


def test_render_plan_hardcut_no_fades():
    plan = video_render_plan(_ab_timeline("cut", 0))
    assert plan["a"]["fades"] == [] and plan["a"]["wipes"] == []
    assert plan["a"]["segments"] == [(0.0, 6.0)]
    assert plan["b"]["segments"] == [(6.0, 12.0)]


def test_render_plan_crossfade_extends_and_fades():
    # cut@6, d=2 → Fenster [5,7]. b erscheint ab 5 mit fade-in, a bleibt bis 7.
    plan = video_render_plan(_ab_timeline("crossfade", 2))
    assert plan["b"]["segments"] == [(5.0, 12.0)]
    assert plan["a"]["segments"] == [(0.0, 7.0)]
    assert plan["b"]["fades"] == [{"type": "in", "st": 5.0, "d": 2.0}]
    assert plan["a"]["fades"] == []


def test_render_plan_wipe():
    plan = video_render_plan(_ab_timeline("wipe", 2))
    assert plan["b"]["wipes"] == [{"st": 5.0, "d": 2.0}]
    assert plan["b"]["segments"] == [(5.0, 12.0)]
    assert plan["a"]["segments"] == [(0.0, 7.0)]


def test_render_plan_fade_black():
    # cut@6, d=2 → a fade-out [5,6], b fade-in [6,7].
    plan = video_render_plan(_ab_timeline("fade-black", 2))
    assert plan["a"]["fades"] == [{"type": "out", "st": 5.0, "d": 1.0}]
    assert plan["b"]["fades"] == [{"type": "in", "st": 6.0, "d": 1.0}]
