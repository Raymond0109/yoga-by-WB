"""Tests for core.landmark_smoother (One Euro Filter + keyframe lock)."""
from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from core.landmark_smoother import LandmarkSmoother, OneEuroFilter


def _flat_pose(val: float = 0.5) -> list[dict]:
    return [{"x": val, "y": val, "z": 0.0, "v": 1.0} for _ in range(33)]


def test_one_euro_reduces_jitter():
    rnd = random.Random(7)
    sm = LandmarkSmoother()
    raw_x: list[float] = []
    sm_x: list[float] = []
    for f in range(60):
        now = f * 0.033
        raw = [{"x": 0.5 + rnd.uniform(-0.02, 0.02), "y": 0.5, "z": 0.0, "v": 1.0} for _ in range(33)]
        out = sm.smooth([dict(p) for p in raw], now=now)
        raw_x.append(raw[0]["x"])
        sm_x.append(out[0]["x"])
    # skip the first few warm-up frames
    assert np.var(sm_x[10:]) < np.var(raw_x[10:]), "smoother should reduce variance"


def test_keyframe_lock_engages_when_static():
    sm = LandmarkSmoother()
    for f in range(6):
        sm.smooth(_flat_pose(0.5), now=f * 0.033)
    assert sm.state == "locked"
    # while locked, returned frame equals the frozen locked pose
    out = sm.smooth(_flat_pose(0.5), now=6 * 0.033)
    assert abs(out[0]["x"] - 0.5) < 1e-6


def test_lock_releases_on_movement():
    sm = LandmarkSmoother()
    for f in range(6):
        sm.smooth(_flat_pose(0.5), now=f * 0.033)
    assert sm.state == "locked"
    # big movement unlocks
    sm.smooth(_flat_pose(0.9), now=6 * 0.033)
    assert sm.state == "tracking"


def test_jump_rejected_returns_last_good():
    sm = LandmarkSmoother()
    base = _flat_pose(0.5)
    sm.smooth([dict(p) for p in base], now=0.0)
    sm.smooth([dict(p) for p in base], now=0.033)
    jumpy = _flat_pose(0.95)  # displacement > jump_threshold (0.15)
    out = sm.smooth([dict(p) for p in jumpy], now=0.066)
    assert abs(out[0]["x"] - 0.5) < 0.05, "jump should be rejected (keep last good)"


def test_preserves_structure_and_visibility():
    lm = [{"x": 0.1, "y": 0.2, "z": 0.3, "v": 0.7} for _ in range(33)]
    sm = LandmarkSmoother()
    out = sm.smooth([dict(p) for p in lm], now=0.0)
    assert len(out) == 33
    assert "v" in out[0]
    assert abs(out[0]["v"] - 0.7) < 1e-9
    # first frame returns the input unchanged
    assert abs(out[0]["x"] - 0.1) < 1e-9


def test_empty_landmarks_passthrough():
    sm = LandmarkSmoother()
    assert sm.smooth([]) == []


def test_smoothing_static_pose_is_near_identity():
    # a held pose should converge to ~itself (no drift)
    sm = LandmarkSmoother()
    ref = [{"x": 0.3 + i * 0.01, "y": 0.4, "z": 0.0, "v": 1.0} for i in range(33)]
    last = None
    for f in range(20):
        last = sm.smooth([dict(p) for p in ref], now=f * 0.033)
    for i in range(33):
        assert abs(last[i]["x"] - ref[i]["x"]) < 1e-3


if __name__ == "__main__":
    import sys

    for name in list(globals()):
        if name.startswith("test_") and callable(globals()[name]):
            globals()[name]()
            print(f"[ok] {name}")
    sys.exit(0)
