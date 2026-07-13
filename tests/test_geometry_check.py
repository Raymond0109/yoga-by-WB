"""Tests for core.geometry_check (bone-length consistency)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.geometry_check import check_skeleton, skeleton_ratios

# Standing T-pose, metric world coords (y-up), torso length ~0.5 m.
# Limb proportions chosen to sit inside the plausible ratio bounds.
_TORSO = 0.5


def _humanoid() -> list[dict]:
    p = [{"x": 0.0, "y": 0.0, "z": 0.0, "v": 1.0} for _ in range(33)]
    p[11] = {"x": -0.10, "y": _TORSO, "z": 0.0, "v": 1.0}      # l_shoulder
    p[12] = {"x": 0.10, "y": _TORSO, "z": 0.0, "v": 1.0}       # r_shoulder
    p[13] = {"x": -0.10, "y": _TORSO - 0.36, "z": 0.0, "v": 1.0}  # l_elbow
    p[14] = {"x": 0.10, "y": _TORSO - 0.36, "z": 0.0, "v": 1.0}   # r_elbow
    p[15] = {"x": -0.10, "y": _TORSO - 0.70, "z": 0.0, "v": 1.0}  # l_wrist
    p[16] = {"x": 0.10, "y": _TORSO - 0.70, "z": 0.0, "v": 1.0}   # r_wrist
    p[23] = {"x": -0.10, "y": 0.0, "z": 0.0, "v": 1.0}         # l_hip
    p[24] = {"x": 0.10, "y": 0.0, "z": 0.0, "v": 1.0}          # r_hip
    p[25] = {"x": -0.10, "y": -0.525, "z": 0.0, "v": 1.0}      # l_knee
    p[26] = {"x": 0.10, "y": -0.525, "z": 0.0, "v": 1.0}       # r_knee
    p[27] = {"x": -0.10, "y": -1.025, "z": 0.0, "v": 1.0}      # l_ankle
    p[28] = {"x": 0.10, "y": -1.025, "z": 0.0, "v": 1.0}       # r_ankle
    return p


def test_valid_pose_is_plausible():
    ok, violations = check_skeleton(_humanoid())
    assert ok, f"expected plausible, got violations: {violations}"
    assert violations == []


def test_corrupted_limb_flagged():
    p = _humanoid()
    # fling the left wrist far away -> impossible forearm length
    p[15] = {"x": -0.10, "y": _TORSO - 3.0, "z": 0.0, "v": 1.0}
    ok, violations = check_skeleton(p)
    assert not ok
    assert any("forearm" in v for v in violations)


def test_ratios_are_torso_normalised():
    r = skeleton_ratios(_humanoid())
    assert r is not None
    # thigh ~1.05, shank ~1.0, upper_arm ~0.72, forearm ~0.68 of torso
    assert 0.9 < r["thigh"] < 1.2
    assert 0.9 < r["shank"] < 1.2
    assert 0.5 < r["upper_arm"] < 1.0
    assert 0.45 < r["forearm"] < 0.95


def test_empty_returns_neutral():
    ok, violations = check_skeleton([])
    assert ok and violations == []


if __name__ == "__main__":
    import glob as _g

    for name in list(globals()):
        if name.startswith("test_") and callable(globals()[name]):
            globals()[name]()
            print(f"[ok] {name}")
