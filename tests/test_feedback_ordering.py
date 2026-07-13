"""Tests for feedback ordering + low-score tip (Item 5).

Items must be returned worst-deviation-first, and `low_score_tip` must be
present only when the overall match score is below 60%.
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.pose_compare as pc


def _blank():
    return [{"x": 0.0, "y": 0.0, "z": 0.0, "v": 1.0} for _ in range(33)]


def _angle_at(deg: float, a: int, b: int, c: int):
    """Landmarks where the angle at vertex `b` (indices a,b,c) equals `deg`."""
    p = _blank()
    p[b] = {"x": 0.0, "y": 0.0, "z": 0.0, "v": 1.0}
    p[a] = {"x": 1.0, "y": 0.0, "z": 0.0, "v": 1.0}
    rad = math.radians(deg)
    p[c] = {"x": math.cos(rad), "y": math.sin(rad), "z": 0.0, "v": 1.0}
    return p


def _three_knee_rules():
    # Same landmarks [23,25,27] with three distinct targets + generous tol,
    # so a single knee angle yields three predictable, distinct deviations.
    return {
        "id": "_order_test",
        "name_en": "t",
        "name_sanskrit": "t",
        "name_zh": "测试",
        "category": "站姿",
        "difficulty": 1,
        "benefits": "",
        "ref_url": "",
        "muscles": [],
        "rules": [
            {"id": "r_low", "type": "joint_angle", "indices": [23, 25, 27],
             "target": 10, "tol": 60, "label": "低目标", "correction": "低纠正"},
            {"id": "r_mid", "type": "joint_angle", "indices": [23, 25, 27],
             "target": 20, "tol": 60, "label": "中目标", "correction": "中纠正"},
            {"id": "r_high", "type": "joint_angle", "indices": [23, 25, 27],
             "target": 30, "tol": 60, "label": "高目标", "correction": "高纠正"},
        ],
    }


def _run(asana, pose):
    saved = pc._cache
    pc._cache = {"version": 1, "asanas": [asana]}
    try:
        return pc.compare(pose, asana["id"])
    finally:
        pc._cache = saved


def test_items_sorted_by_abs_deviation_desc():
    a = _three_knee_rules()
    pose = _angle_at(170, 23, 25, 27)  # devs: 160, 150, 140
    fb = _run(a, pose)
    devs = [abs(i["deviation"]) for i in fb["items"]]
    assert devs == sorted(devs, reverse=True)
    assert fb["items"][0]["id"] == "r_low"  # largest deviation first


def test_low_score_tip_none_when_high():
    a = _three_knee_rules()
    pose = _angle_at(20, 23, 25, 27)  # devs: 10, 0, 10 -> all within tol
    fb = _run(a, pose)
    assert fb["score"] >= 60
    assert fb.get("low_score_tip") is None


def test_low_score_tip_present_when_low():
    a = _three_knee_rules()
    pose = _angle_at(170, 23, 25, 27)  # all item_scores 0 -> overall 0
    fb = _run(a, pose)
    assert fb["score"] < 60
    tip = fb.get("low_score_tip")
    assert tip is not None
    assert "低目标" in tip  # worst rule's label
    assert "低纠正" in tip  # worst rule's correction
