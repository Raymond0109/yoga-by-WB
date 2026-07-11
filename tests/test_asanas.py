"""Backend sanity tests for the asana DB + compare engine.

Run: python tests/test_asanas.py   (managed venv, py3.13)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pose_compare import load_db, compare, detect_asana, get_asana_list


def _blank(n=33):
    return [{"x": 0.0, "y": 0.0, "z": 0.0, "v": 1.0} for _ in range(n)]


def _handstand_world():
    """Synthetic inverted vertical handstand (y-up, hip centre at origin)."""
    p = _blank()
    p[11] = {"x": -0.1, "y": -0.5, "z": 0, "v": 1}   # l_shoulder
    p[12] = {"x": 0.1, "y": -0.5, "z": 0, "v": 1}    # r_shoulder
    p[13] = {"x": -0.1, "y": -0.75, "z": 0, "v": 1}  # l_elbow
    p[14] = {"x": 0.1, "y": -0.75, "z": 0, "v": 1}   # r_elbow
    p[15] = {"x": -0.1, "y": -1.0, "z": 0, "v": 1}   # l_wrist (on floor)
    p[16] = {"x": 0.1, "y": -1.0, "z": 0, "v": 1}    # r_wrist
    p[23] = {"x": -0.1, "y": 0.0, "z": 0, "v": 1}    # l_hip
    p[24] = {"x": 0.1, "y": 0.0, "z": 0, "v": 1}     # r_hip
    p[25] = {"x": -0.1, "y": 0.5, "z": 0, "v": 1}    # l_knee
    p[26] = {"x": 0.1, "y": 0.5, "z": 0, "v": 1}     # r_knee
    p[27] = {"x": -0.1, "y": 1.0, "z": 0, "v": 1}    # l_ankle (top)
    p[28] = {"x": 0.1, "y": 1.0, "z": 0, "v": 1}     # r_ankle
    return p


def _tree_world():
    """Synthetic standing tree pose, arms overhead (y-up, hip centre origin)."""
    p = _blank()
    p[11] = {"x": -0.1, "y": 0.5, "z": 0, "v": 1}    # l_shoulder
    p[12] = {"x": 0.1, "y": 0.5, "z": 0, "v": 1}     # r_shoulder
    p[13] = {"x": -0.1, "y": 0.75, "z": 0, "v": 1}   # l_elbow
    p[14] = {"x": 0.1, "y": 0.75, "z": 0, "v": 1}    # r_elbow
    p[15] = {"x": -0.1, "y": 1.0, "z": 0, "v": 1}    # l_wrist (above shoulder)
    p[16] = {"x": 0.1, "y": 1.0, "z": 0, "v": 1}     # r_wrist
    p[23] = {"x": -0.1, "y": 0.0, "z": 0, "v": 1}    # l_hip
    p[24] = {"x": 0.1, "y": 0.0, "z": 0, "v": 1}     # r_hip
    p[25] = {"x": -0.1, "y": -0.5, "z": 0, "v": 1}   # l_knee (stand leg)
    p[26] = {"x": 0.3, "y": -0.1, "z": 0.1, "v": 1}  # r_knee (foot on thigh)
    p[27] = {"x": -0.1, "y": -1.0, "z": 0, "v": 1}   # l_ankle
    p[28] = {"x": 0.1, "y": -0.1, "z": 0.15, "v": 1} # r_ankle
    return p


def main():
    db = load_db()
    n = len(db["asanas"])
    assert n == 23, f"expected 23 asanas, got {n}"
    print(f"[ok] asana count = {n}")

    # handstand self-score should be 100
    hs = _handstand_world()
    fb_hs = compare(hs, "handstand")
    assert fb_hs["score"] == 100, f"handstand self score = {fb_hs['score']}"
    print(f"[ok] handstand self score = {fb_hs['score']}")

    # tree self-score should be 100
    tr = _tree_world()
    fb_tr = compare(tr, "tree")
    assert fb_tr["score"] == 100, f"tree self score = {fb_tr['score']}"
    print(f"[ok] tree self score = {fb_tr['score']}")

    # vertical_order item must carry a unit and arrow value
    vo = next(i for i in fb_hs["items"] if i["id"] == "hands_below_shoulders")
    assert vo["unit"] == "" and vo["status"] == "ok" and "↓" in str(vo["value"])
    print(f"[ok] vertical_order renders: {vo['value']} (target {vo['target']}, {vo['status']})")

    # KEY: a handstand pose must NOT be detected as tree, and vice versa
    det_hs = detect_asana(hs)
    assert det_hs["id"] == "handstand", f"handstand detected as {det_hs['id']}"
    det_tr = detect_asana(tr)
    assert det_tr["id"] == "tree", f"tree detected as {det_tr['id']}"
    print(f"[ok] detect(handstand pose) -> {det_hs['id']} {det_hs['score']}%")
    print(f"[ok] detect(tree pose)      -> {det_tr['id']} {det_tr['score']}%")

    # regression: a real handstand must beat tree for that input
    tree_score_on_hs = compare(hs, "tree")["score"]
    print(f"[ok] tree score on handstand input = {tree_score_on_hs}% (must be < handstand 100%)")
    assert tree_score_on_hs < 100

    # every asana id must be selectable and compare returns items
    for a in get_asana_list():
        f = compare(hs, a["id"])
        assert f and f["items"], f"{a['id']} returned no items"
    print("[ok] all asanas compare() without error")

    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    main()
