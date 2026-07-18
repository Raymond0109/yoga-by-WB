"""Tests for continuous (deviation-based) scoring in core.pose_compare."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.pose_compare as pc


def _make_fake_asana():
    # one joint_angle rule: front knee target 90, tol 20
    return {
        "id": "_scoring_test",
        "name_en": "t",
        "name_sanskrit": "t",
        "name_zh": "测试",
        "category": "站姿",
        "difficulty": 1,
        "benefits": "",
        "ref_url": "",
        "muscles": [],
        "rules": [
            {
                "id": "knee",
                "type": "joint_angle",
                "indices": [23, 25, 27],
                "target": 90,
                "tol": 20,
                "label": "前膝",
                "correction": "x",
            }
        ],
    }


def _blank():
    return [{"x": 0.0, "y": 0.0, "z": 0.0, "v": 1.0} for _ in range(33)]


def _knee_angle(deg: float):
    """Landmarks where the angle at the knee (23-25-27) equals `deg`."""
    p = _blank()
    # 25 at origin; arm1 toward +x (23), arm2 rotated by `deg` from arm1
    import math

    p[25] = {"x": 0.0, "y": 0.0, "z": 0.0, "v": 1.0}
    p[23] = {"x": 1.0, "y": 0.0, "z": 0.0, "v": 1.0}  # arm1 = (1,0)
    rad = math.radians(deg)
    p[27] = {"x": math.cos(rad), "y": math.sin(rad), "z": 0.0, "v": 1.0}  # arm2
    return p


def setup_module(module):
    pc._cache = {"version": 1, "asanas": [_make_fake_asana()]}


def test_perfect_within_tol_is_100():
    fb = pc.compare(_knee_angle(90), "_scoring_test")
    assert fb["score"] == 100
    assert fb["items"][0]["item_score"] == 100.0
    assert fb["items"][0]["status"] == "ok"


def test_partial_in_warn_zone():
    # 60 deg -> deviation 30 = 1.5*tol -> item_score = 100*(1-(30-20)/20)=50
    fb = pc.compare(_knee_angle(60), "_scoring_test")
    assert fb["items"][0]["item_score"] == 50.0
    assert fb["score"] == 50
    assert fb["items"][0]["status"] == "warn"


def test_beyond_warn_zone_is_zero():
    # 40 deg -> deviation 50 > 2*tol(40) -> item_score 0, overall 0
    fb = pc.compare(_knee_angle(40), "_scoring_test")
    assert fb["items"][0]["item_score"] == 0.0
    assert fb["score"] == 0
    assert fb["items"][0]["status"] == "off"


def test_level_tol_is_centimeters_not_auto_scaled():
    """B2: level tol must stay in cm; never multiply by 100 when tol < 1."""
    pc._cache = {
        "version": 1,
        "asanas": [{
            "id": "_level_test",
            "name_en": "t", "name_sanskrit": "t", "name_zh": "t",
            "category": "站姿", "difficulty": 1, "benefits": "", "ref_url": "",
            "muscles": [],
            "rules": [{
                "id": "pelvis_level",
                "type": "level",
                "indices": [23, 24],
                "tol": 0.863,  # cm — previously wrongly scaled to 86.3
                "label": "骨盆水平",
                "correction": "x",
            }],
        }],
    }
    p = _blank()
    # 5 cm hip height difference (world y * 100)
    p[23] = {"x": -0.1, "y": 0.0, "z": 0.0, "v": 1.0}
    p[24] = {"x": 0.1, "y": 0.05, "z": 0.0, "v": 1.0}
    fb = pc.compare(p, "_level_test")
    assert fb["items"][0]["tol"] == 0.863
    assert fb["items"][0]["value"] == 5.0
    # 5 cm >> 0.863 cm → off, not ok
    assert fb["items"][0]["status"] == "off"
    assert fb["items"][0]["item_score"] == 0.0


def test_vertical_order_partial_score():
    """B6: order rules should give partial credit, not only 0/100."""
    pc._cache = {
        "version": 1,
        "asanas": [{
            "id": "_order_score_test",
            "name_en": "t", "name_sanskrit": "t", "name_zh": "t",
            "category": "站姿", "difficulty": 1, "benefits": "", "ref_url": "",
            "muscles": [],
            "rules": [{
                "id": "arms_up",
                "type": "vertical_order",
                # Real tree convention: indices=[wrist, shoulder], target=-1
                # means wrist above shoulder (dy = y_sh - y_wrist < 0).
                "indices": [15, 11],
                "target": -1,
                "min_sep": 20.0,
                "label": "手臂上举",
                "correction": "x",
            }],
        }],
    }
    # Perfect: wrist 30 cm above shoulder
    p = _blank()
    p[11] = {"x": 0.0, "y": 0.0, "z": 0.0, "v": 1.0}
    p[15] = {"x": 0.0, "y": 0.30, "z": 0.0, "v": 1.0}
    fb = pc.compare(p, "_order_score_test")
    assert fb["items"][0]["status"] == "ok"
    assert fb["items"][0]["item_score"] == 100.0

    # Partial: correct side but only 10 cm (min_sep=20) → shortfall 10
    # synthetic tol = max(20*0.5, 1) = 10; iscore = 100*(1 - 10/(2*10)) = 50
    p[15] = {"x": 0.0, "y": 0.10, "z": 0.0, "v": 1.0}
    fb = pc.compare(p, "_order_score_test")
    assert fb["items"][0]["status"] == "off"  # not separated enough
    assert fb["items"][0]["item_score"] == 50.0


if __name__ == "__main__":
    setup_module(None)
    for name in list(globals()):
        if name.startswith("test_") and callable(globals()[name]):
            globals()[name]()
            print(f"[ok] {name}")
