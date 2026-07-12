"""WYSIWYG-Assemblierung der A/B-Roll-Timeline für den Export.

Spiegelt die Frontend-Logik (assembleOutput.activeVideoAt): Der Output toggelt
an jedem Schnittpunkt zwischen der ersten und zweiten Video-Spur (gerade Anzahl
Schnittpunkte ≤ t → erste, ungerade → zweite) und fällt bei einer Lücke in der
aktiven Spur auf die andere Video-Spur zurück. Bei nur einer Video-Spur ist
diese immer aktiv. Rein funktional gehalten, damit unabhängig vom FFmpeg-Aufruf
testbar.
"""
from __future__ import annotations


def _clip_at(track: dict, t: float) -> dict | None:
    """Letzter Clip der Spur, der t abdeckt (überlappende Clips: späterer gewinnt)."""
    hit: dict | None = None
    for clip in track.get("clips", []):
        start = clip["start"]
        if start <= t < start + clip["duration"]:
            hit = clip
    return hit


def _video_tracks(timeline: dict) -> list[dict]:
    """Video-kind-Spuren in Timeline-Reihenfolge (A = erste, B = zweite)."""
    return [t for t in timeline.get("tracks", []) if t.get("kind") == "video" and not t.get("muted")]


def _active_clip_at(video_tracks: list[dict], cut_times: list[float], t: float) -> dict | None:
    """Sichtbarer Video-Clip an t: aktive Spur nach Schnittpunkt-Toggle (A/B),
    Fallback auf die jeweils andere Video-Spur bei Lücke."""
    if not video_tracks:
        return None
    n_before = sum(1 for ct in cut_times if ct <= t)
    primary_idx = n_before % 2 if len(video_tracks) > 1 else 0
    order = [primary_idx] + [i for i in range(len(video_tracks)) if i != primary_idx]
    for i in order:
        clip = _clip_at(video_tracks[i], t)
        if clip is not None:
            return clip
    return None


def _merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Sortiert und verschmilzt angrenzende/überlappende Intervalle."""
    if not intervals:
        return []
    ordered = sorted(intervals)
    merged = [ordered[0]]
    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + 1e-6:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


def video_onair_segments(timeline: dict) -> dict[str, list[tuple[float, float]]]:
    """Je Video-Clip die disjunkten Zeit-Intervalle, in denen er im Output sichtbar
    ist. Die Zeitachse wird an allen Ereignispunkten (0, Clip-Kanten, Schnittpunkte)
    in Elementar-Intervalle zerlegt; am Mittelpunkt jedes Intervalls wird der aktive
    Clip bestimmt."""
    video_tracks = _video_tracks(timeline)
    cut_times = sorted(cp["time"] for cp in timeline.get("cut_points", []))

    # Ereigniszeitpunkte sammeln.
    boundaries: set[float] = {0.0}
    for track in video_tracks:
        for clip in track.get("clips", []):
            boundaries.add(float(clip["start"]))
            boundaries.add(float(clip["start"] + clip["duration"]))
    for ct in cut_times:
        boundaries.add(float(ct))

    points = sorted(boundaries)
    segments: dict[str, list[tuple[float, float]]] = {}
    for left, right in zip(points, points[1:]):
        if right - left <= 1e-9:
            continue
        mid = (left + right) / 2
        clip = _active_clip_at(video_tracks, cut_times, mid)
        if clip is None:
            continue
        segments.setdefault(clip["id"], []).append((left, right))

    return {clip_id: _merge_intervals(ivals) for clip_id, ivals in segments.items()}
