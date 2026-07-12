from hydrahive.media_timeline_assembly import video_onair_segments


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
