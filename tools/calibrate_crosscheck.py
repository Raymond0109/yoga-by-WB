"""Cross-calibration check against the sibling repo's reference DB.

The sibling project (yoga-pose-analyzer) ships a 38-pose standard DB with
per-joint target angles derived from anatomy-image analysis
(src/core/comparison/StandardPoseDB.ts). This script maps those reference
angles onto OUR comparable rules (joint_angle knees/elbows, bone_orientation
thighs/arms) and prints divergences, so we can sanity-check our hand-tuned
targets against an independent second source.

It does NOT modify data/asanas.json — it only reports. Run:
    python tools/calibrate_crosscheck.py
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pose_compare import load_db

# Reference jointAngles (id -> {kneeL,kneeR,hipL,hipR,shL,shR,elL,elR})
# Sourced from yoga-pose-analyzer StandardPoseDB.ts (2026-07-12).
REF = {
    "tadasana": (178, 178, 178, 178, 175, 175, 178, 178),
    "vrksasana": (175, 45, 175, 60, 160, 160, None, None),
    "adho_mukha_svanasana": (175, 175, 65, 65, 170, 170, 175, 175),
    "utkatasana": (95, 95, 90, 90, 170, 170, 178, 178),
    "balasana": (90, 90, 45, 45, 160, 160, None, None),
    "bhujangasana": (175, 175, 160, 160, 100, 100, 150, 150),
    "setu_bandhasana": (100, 100, 120, 120, 170, 170, None, None),
    "ustrasana": (100, 100, 150, 150, 130, 130, None, None),
    "baddha_konasana": (110, 110, 80, 80, 150, 150, 160, 160),
    "savasana": (175, 175, 175, 175, 175, 175, None, None),
    "bharadvajasana_i": (100, 100, 90, 90, 130, 130, None, None),
    "padangusthasana": (175, 175, 45, 45, 150, 150, None, None),
    "chakravakasana": (100, 100, 120, 120, 160, 160, None, None),
    "sukhasana": (110, 110, 80, 80, 150, 150, None, None),
    "utthita_ashwa_sanchalanasana": (95, 170, 95, 160, 170, 170, None, None),
    "prasarita_padottanasana": (175, 175, 60, 60, 150, 150, None, None),
    "vajrasana": (30, 30, 170, 170, 170, 170, 160, 160),
    "paschimottanasana": (175, 175, 45, 45, 160, 160, 170, 170),
    "salamba_bhujangasana": (175, 175, 170, 170, 100, 100, 90, 90),
    "supta_matsyendrasana": (90, 90, 90, 90, 170, 170, 175, 175),
    "virabhadrasana_i": (90, 178, 90, 175, 170, 170, 178, 178),
    "virabhadrasana_ii": (90, 178, 90, 175, 90, 90, 178, 178),
    "trikonasana": (178, 178, 120, 170, 170, 170, 178, 178),
    "utthita_parsvakonasana": (90, 175, 95, 140, 120, 40, None, None),
    "plank": (175, 175, 170, 170, 170, 170, 175, 175),
    "ardha_matsyendrasana": (100, 100, 90, 90, 130, 130, None, None),
    "kapotasana": (100, 160, 90, 160, 150, 150, None, None),
    "sarvangasana": (175, 175, 175, 175, 150, 150, None, None),
    "dhanurasana": (120, 120, 160, 160, 140, 140, None, None),
    "gomukhasana": (110, 110, 80, 80, 150, 150, None, None),
    "ardha_pincha_mayurasana": (175, 175, 90, 90, 160, 160, None, None),
    "garudasana": (175, 45, 175, 60, 140, 140, None, None),
    "virabhadrasana_iii": (175, 175, 170, 170, 170, 170, None, None),
    "natarajasana": (175, 90, 175, 130, 170, 150, None, None),
    "chaturanga": (175, 175, 175, 175, 100, 100, 100, 100),
    "navasana": (175, 175, 50, 50, 60, 60, None, None),
    "bakasana": (110, 110, 90, 90, 120, 120, 100, 100),
    "sirsasana": (175, 175, 175, 175, 150, 150, None, None),
}

# which reference joint each of OUR rule types/indices corresponds to
def _ref_key(indices, kind):
    # knee / elbow -> joint_angle; thigh/arm -> bone_orientation
    if kind == "joint_angle":
        if indices == [23, 25, 27]:
            return "kneeL"
        if indices == [24, 26, 28]:
            return "kneeR"
        if indices == [11, 13, 15]:
            return "elL"
        if indices == [12, 14, 16]:
            return "elR"
    if kind == "bone_orientation":
        if indices == [23, 25]:
            return "hipL"  # thigh-to-vertical ~ hip flexion
        if indices == [24, 26]:
            return "hipR"
        if indices in ([11, 15], [12, 16]):
            return "sh"  # arm-to-vertical; ref shoulder ~= 180 - this
    return None


def main():
    db = load_db()
    print("Cross-calibration: OUR rule target vs sibling reference\n")
    print(f"{'our_id':24s} {'rule':22s} {'ref_joint':9s} {'ours':>5s} {'ref':>5s} {'Δ':>5s}")
    print("-" * 78)
    flagged = 0
    for a in db["asanas"]:
        oid = a["id"]
        if oid not in REF:
            continue
        ref = REF[oid]
        ref_map = {
            "kneeL": ref[0], "kneeR": ref[1], "hipL": ref[2], "hipR": ref[3],
            "shL": ref[4], "shR": ref[5], "elL": ref[6], "elR": ref[7],
        }
        for r in a["rules"]:
            key = _ref_key(r.get("indices", []), r["type"])
            if key is None:
                continue
            if key == "sh":
                # arm bone_orientation (0=vertical) vs ref shoulder (180=down/vertical arm)
                ours = r.get("target")
                refv = ref_map.get("shL")
                if refv is None:
                    continue
                # comparable: ref shoulder 170 (arm up) ~ our bone_orientation 10
                delta = abs((180 - refv) - ours)
            else:
                ours = r.get("target")
                refv = ref_map.get(key)
                if refv is None:
                    continue
                delta = abs(refv - ours)
            mark = ""
            if delta > 12:
                mark = "  <-- diverge"
                flagged += 1
            print(f"{oid:24s} {r['id']:22s} {key:9s} {ours:5} {refv:5} {delta:5.0f}{mark}")
    print("-" * 78)
    print(f"flagged divergences (>12 deg): {flagged}")


if __name__ == "__main__":
    main()
