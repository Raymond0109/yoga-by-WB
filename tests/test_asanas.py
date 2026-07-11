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


def _camel_world():
    """Synthetic kneeling camel backbend (y-up, hip centre origin)."""
    p = _blank()
    p[11] = {"x": 0.05, "y": -0.05, "z": -0.2, "v": 1}   # l_shoulder (back)
    p[12] = {"x": -0.05, "y": -0.20, "z": -0.1, "v": 1}  # r_shoulder
    p[13] = {"x": 0.20, "y": -0.30, "z": -0.3, "v": 1}  # l_elbow (hand down)
    p[14] = {"x": -0.15, "y": -0.35, "z": -0.2, "v": 1} # r_elbow
    p[15] = {"x": 0.30, "y": -0.50, "z": -0.4, "v": 1}  # l_wrist (near heel)
    p[16] = {"x": -0.20, "y": 0.10, "z": -0.2, "v": 1}  # r_wrist (up)
    p[23] = {"x": 0.02, "y": 0.05, "z": -0.05, "v": 1}  # l_hip
    p[24] = {"x": -0.02, "y": -0.05, "z": 0.05, "v": 1} # r_hip
    p[25] = {"x": 0.02, "y": 0.30, "z": -0.10, "v": 1}  # l_knee (below hip)
    p[26] = {"x": -0.02, "y": 0.25, "z": 0.05, "v": 1}  # r_knee
    p[27] = {"x": 0.30, "y": 0.50, "z": 0.05, "v": 1}   # l_ankle (above hip)
    p[28] = {"x": -0.30, "y": 0.45, "z": 0.15, "v": 1}  # r_ankle
    return p


def _gate_world():
    """Synthetic kneeling side-bend Gate (Parighasana), y-up, hip-centre origin."""
    p = _blank()
    p[11] = {"x": -0.35, "y": 0.35, "z": 0, "v": 1}   # l_shoulder (side-bent)
    p[12] = {"x": 0.20, "y": 0.40, "z": 0, "v": 1}    # r_shoulder
    p[13] = {"x": -0.35, "y": 0.60, "z": 0, "v": 1}   # l_elbow (up)
    p[14] = {"x": 0.50, "y": 0.35, "z": 0, "v": 1}    # r_elbow (to foot)
    p[15] = {"x": -0.40, "y": 0.85, "z": 0, "v": 1}   # l_wrist (overhead)
    p[16] = {"x": 0.90, "y": 0.10, "z": 0, "v": 1}    # r_wrist (to foot)
    p[23] = {"x": 0.0, "y": 0.0, "z": 0, "v": 1}      # l_hip
    p[24] = {"x": 0.0, "y": 0.0, "z": 0, "v": 1}      # r_hip
    p[25] = {"x": 0.0, "y": -0.90, "z": 0, "v": 1}    # l_knee (kneeling)
    p[26] = {"x": 0.45, "y": 0.0, "z": 0, "v": 1}     # r_knee (extended side)
    p[27] = {"x": 0.0, "y": -0.90, "z": 0, "v": 1}    # l_ankle (tucked)
    p[28] = {"x": 0.90, "y": 0.0, "z": 0, "v": 1}     # r_ankle (side)
    return p


def _low_lunge_world():
    """Synthetic Low Lunge (Anjaneyasana), y-up, hip-centre origin."""
    p = _blank()
    p[11] = {"x": 0.05, "y": 0.50, "z": 0, "v": 1}    # l_shoulder (up)
    p[12] = {"x": -0.05, "y": 0.50, "z": 0, "v": 1}   # r_shoulder
    p[13] = {"x": 0.05, "y": 0.75, "z": 0, "v": 1}    # l_elbow
    p[14] = {"x": -0.05, "y": 0.75, "z": 0, "v": 1}   # r_elbow
    p[15] = {"x": 0.05, "y": 1.00, "z": 0, "v": 1}    # l_wrist (up)
    p[16] = {"x": -0.05, "y": 1.00, "z": 0, "v": 1}   # r_wrist (up)
    p[23] = {"x": 0.0, "y": 0.0, "z": 0, "v": 1}      # l_hip
    p[24] = {"x": 0.0, "y": 0.0, "z": 0, "v": 1}      # r_hip
    p[25] = {"x": 0.40, "y": -0.40, "z": 0, "v": 1}   # l_knee (front, low)
    p[26] = {"x": -0.50, "y": -0.05, "z": 0, "v": 1}  # r_knee (back, extended)
    p[27] = {"x": 0.40, "y": -0.90, "z": 0, "v": 1}   # l_ankle (front foot)
    p[28] = {"x": -1.00, "y": -0.10, "z": 0, "v": 1}  # r_ankle (back foot)
    return p


def _side_angle_world():
    """Synthetic Side Angle (Utthita Parsvakonasana), y-up, hip-centre origin.

    Faithful geometry: front thigh parallel to floor, torso folded FORWARD
    over it (~70 deg from vertical, not an upright 45), top arm overhead,
    bottom arm reaching down to the floor/in front.
    """
    p = _blank()
    p[11] = {"x": 0.60, "y": 0.20, "z": 0, "v": 1}    # l_shoulder (forward-folded)
    p[12] = {"x": 0.10, "y": 0.50, "z": 0, "v": 1}    # r_shoulder (up)
    p[13] = {"x": 0.60, "y": 0.00, "z": 0, "v": 1}    # l_elbow
    p[14] = {"x": 0.10, "y": 0.75, "z": 0, "v": 1}    # r_elbow
    p[15] = {"x": 0.55, "y": -0.45, "z": 0, "v": 1}   # l_wrist (bottom arm down)
    p[16] = {"x": 0.15, "y": 1.00, "z": 0, "v": 1}    # r_wrist (top arm overhead)
    p[23] = {"x": 0.0, "y": 0.0, "z": 0, "v": 1}      # l_hip
    p[24] = {"x": 0.0, "y": 0.0, "z": 0, "v": 1}      # r_hip
    p[25] = {"x": 0.40, "y": 0.0, "z": 0, "v": 1}     # l_knee (front thigh flat)
    p[26] = {"x": -0.50, "y": 0.0, "z": 0, "v": 1}    # r_knee (back, extended)
    p[27] = {"x": 0.40, "y": -0.90, "z": 0, "v": 1}   # l_ankle (front foot)
    p[28] = {"x": -1.00, "y": 0.0, "z": 0, "v": 1}    # r_ankle (back foot)
    return p


def main():
    db = load_db()
    n = len(db["asanas"])
    # 24 original asanas + 3 added in v0.5.3 (gate, low_lunge, side_angle).
    # Note: warrior1 already existed in the original 24, so it is NOT a new id.
    assert n == 27, f"expected 27 asanas, got {n}"
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

    # camel self-score should be 100 and a kneeling camel must not be mis-detected as prone locust
    cam = _camel_world()
    fb_cam = compare(cam, "camel")
    assert fb_cam["score"] == 100, f"camel self score = {fb_cam['score']}"
    det_cam = detect_asana(cam)
    assert det_cam["id"] == "camel", f"camel detected as {det_cam['id']} {det_cam['score']}%"
    print(f"[ok] camel self score = {fb_cam['score']} and detected as {det_cam['id']} {det_cam['score']}%")

    # regression: camel must beat salabhasana (the screenshot mis-detection)
    sal_score_on_cam = compare(cam, "salabhasana")["score"]
    assert sal_score_on_cam < fb_cam["score"], f"salabhasana {sal_score_on_cam}% >= camel {fb_cam['score']}%"
    print(f"[ok] salabhasana score on camel input = {sal_score_on_cam}% (must be < camel 100%)")

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

    # v0.5.3 additions: gate / low_lunge / side_angle must self-detect at 100%
    # and must NOT be shadowed by a geometrically similar existing pose.
    g = _gate_world()
    fb_g = compare(g, "gate")
    assert fb_g["score"] == 100, f"gate self score = {fb_g['score']}"
    det_g = detect_asana(g)
    assert det_g["id"] == "gate", f"gate detected as {det_g['id']} {det_g['score']}%"
    assert compare(g, "cobra")["score"] < 100, "gate input must not also score cobra 100%"
    print(f"[ok] gate self score = {fb_g['score']} and detected as {det_g['id']} {det_g['score']}%")

    l = _low_lunge_world()
    fb_l = compare(l, "low_lunge")
    assert fb_l["score"] == 100, f"low_lunge self score = {fb_l['score']}"
    det_l = detect_asana(l)
    assert det_l["id"] == "low_lunge", f"low_lunge detected as {det_l['id']} {det_l['score']}%"
    print(f"[ok] low_lunge self score = {fb_l['score']} and detected as {det_l['id']} {det_l['score']}%")

    s = _side_angle_world()
    fb_s = compare(s, "side_angle")
    assert fb_s["score"] == 100, f"side_angle self score = {fb_s['score']}"
    det_s = detect_asana(s)
    assert det_s["id"] == "side_angle", f"side_angle detected as {det_s['id']} {det_s['score']}%"
    assert compare(s, "urdhva_dhanurasana")["score"] < 100, "side_angle input must not also score wheel 100%"
    print(f"[ok] side_angle self score = {fb_s['score']} and detected as {det_s['id']} {det_s['score']}%")

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
