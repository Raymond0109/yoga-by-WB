"""Skeleton geometry-consistency check.

A lightweight, per-frame sanity net on top of MediaPipe output. It measures
the major limb lengths *relative to torso length* and flags poses whose
proportions are anatomically impossible (e.g. a forearm 4x the torso, or a
collapsed hip). Such glitches are rare but, when they happen, they produce
nonsensical feedback — so we surface a ``skeleton_ok`` flag to the client
and can down-weight/ignore the frame.

The bounds are deliberately generous (they catch gross errors, not normal
body-shape variation) so they never false-positive on a real pose.
"""
from __future__ import annotations

import math
from typing import Optional

# (left, right) torso segments — used as the scale reference.
_TORSO = ((11, 23), (12, 24))
# limb bone segments (MediaPipe indices)
_LIMBS = {
    "upper_arm": ((11, 13), (12, 14)),
    "forearm": ((13, 15), (14, 16)),
    "thigh": ((23, 25), (24, 26)),
    "shank": ((25, 27), (26, 28)),
}
# generous plausible bounds for limb/torso ratio (covers most body types)
_RATIO_BOUNDS = {
    "upper_arm": (0.45, 1.05),
    "forearm": (0.40, 0.95),
    "thigh": (0.75, 1.35),
    "shank": (0.70, 1.30),
}


def _dist(a, b) -> float:
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"], a["z"] - b["z"])


def skeleton_ratios(landmarks: list[dict]) -> Optional[dict]:
    """Return {limb: length / torso_length} or None if degenerate."""
    if not landmarks or len(landmarks) < 29:
        return None
    torso = sum(_dist(landmarks[a], landmarks[b]) for a, b in _TORSO) / len(_TORSO)
    if torso < 1e-6:
        return None
    out = {}
    for name, segs in _LIMBS.items():
        lengths = [_dist(landmarks[a], landmarks[b]) for a, b in segs]
        out[name] = sum(lengths) / len(lengths) / torso
    return out


def check_skeleton(landmarks: list[dict]) -> tuple[bool, list[str]]:
    """Return (ok, violations[]). ``ok`` is False when any limb ratio falls
    outside its plausible bounds."""
    ratios = skeleton_ratios(landmarks)
    if ratios is None:
        return True, []  # not enough data to judge -> don't block
    violations = []
    for name, (lo, hi) in _RATIO_BOUNDS.items():
        r = ratios[name]
        if r < lo or r > hi:
            violations.append(f"{name}: ratio {r:.2f} outside [{lo}, {hi}]")
    return (len(violations) == 0), violations
