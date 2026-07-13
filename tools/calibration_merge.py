"""Refined conservative merge of calibration suggestions into a STAGING copy.

Policy (anatomy-safe — never writes data/asanas.json directly):
  * refs < 3  (SINGLE) ........ keep current target & tol  (too weak)
  * refs == 0  (UNCAL) ........ keep current  (crow/handstand/extended_hand_to_toe)
  * refs >= 3 ................
      - TARGETS: apply the video mean ONLY when the current target is NOT a
        near-extreme alignment (straight leg / right angle / vertical / horizontal
        intent). Those are protected at their anatomical value so we never encode
        a noisy video mean that bends a straight leg or tilts a vertical limb.
      - TOLERANCES: only WIDEN (never tighten) vs current, then clamp to sane
        maxima. Widening can't break the existing synthetic-test poses, while
        still absorbing the video-demonstrated variation.
      - vertical_order: keep current direction; widen min_sep only.
      - level: keep target 0; widen tol only.

Tol clamps: joint_angle/bone_orientation <= 30 deg, level <= 10 cm,
vertical_order min_sep in [15, 40] cm.

Writes data/asanas.merged.json and prints a change summary for review.
"""
from __future__ import annotations
import json, os, glob

CUR = "data/asanas.json"
SUG = "data/asanas.suggested.json"
REF = "data/ref"
OUT = "data/asanas.merged.json"

MAX_TOL_DEG = 30.0
MAX_TOL_CM = 10.0
MIN_SEP = 15.0
MAX_SEP = 40.0
MIN_TOL_DEG = 5.0
# Video means are single-source & noisy; only accept a target nudge when it
# CONVERGES with the expert-authored alignment (<= this delta). Large shifts are
# treated as video bias (loose form / world-landmark projection skew) and the
# expert alignment target is kept. Tolerances are still widened from video.
TARGET_MAX_DELTA = 8.0


def refcount(aid):
    d = os.path.join(REF, aid)
    return len(glob.glob(os.path.join(d, "ref_*.json"))) if os.path.isdir(d) else 0


def is_extreme(t, cur):
    """True for straight/right-angle/vertical/horizontal intent -> protect."""
    if t == "joint_angle":
        return cur <= 20 or cur >= 160
    if t == "bone_orientation":
        return cur <= 15 or cur >= 75
    return False


def clamp_target(t, v):
    if t == "joint_angle":
        return max(0.0, min(180.0, v))
    if t == "bone_orientation":
        return max(0.0, min(90.0, v))
    return v


cur = json.load(open(CUR))
sug = json.load(open(SUG))
by_id = {a["id"]: a for a in sug["asanas"]}

target_changes, tol_changes = [], []
for a in cur["asanas"]:
    aid = a["id"]
    rc = refcount(aid)
    sa = by_id.get(aid)
    for r in a["rules"]:
        rid = r["id"]
        sr = next((x for x in sa["rules"] if x["id"] == rid), None) if sa else None
        if rc < 3 or not sr:
            continue
        t = r["type"]
        cur_t = r.get("target", 0)
        sug_t = sr.get("target", cur_t)
        # ---- target (protected near-extremes) ----
        if t in ("joint_angle", "bone_orientation"):
            if not is_extreme(t, cur_t):
                nt = clamp_target(t, sug_t)
                # only nudge when video CONVERGES with expert alignment
                if 0.05 < abs(nt - cur_t) <= TARGET_MAX_DELTA:
                    target_changes.append((aid, rid, cur_t, round(nt, 1)))
                    r["target"] = round(nt, 1)
        elif t == "vertical_order":
            pass  # direction kept; handled via min_sep below
        # ---- tol (widen only, then clamp) ----
        if t == "vertical_order":
            # min_sep is a THRESHOLD (sep >= min_sep to satisfy), NOT a tolerance.
            # Raising it TIGHTENS the rule and can break pose discrimination
            # (e.g. low_lunge back_foot_low). Keep current min_sep untouched.
            pass
        elif t == "level":
            sug_tol = sr.get("tol", r.get("tol"))
            ntol = max(r.get("tol", 0.03), min(MAX_TOL_CM, sug_tol))
            if abs(ntol - r.get("tol", 0)) > 0.001:
                tol_changes.append((aid, rid, "tol", r.get("tol"), round(ntol, 3)))
            r["tol"] = round(ntol, 3)
        else:
            sug_tol = sr.get("tol", r.get("tol"))
            ntol = max(r.get("tol", MIN_TOL_DEG), min(MAX_TOL_DEG, sug_tol))
            if abs(ntol - r.get("tol", 0)) > 0.05:
                tol_changes.append((aid, rid, "tol", r.get("tol"), round(ntol, 1)))
            r["tol"] = round(ntol, 1)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(cur, f, ensure_ascii=False, indent=2)

print(f"Wrote staging -> {OUT}")
print(f"\nTARGET changes ({len(target_changes)}) [near-extreme protected]:")
for aid, rid, old, new in target_changes:
    print(f"  {aid:22s} {rid:20s} {old} -> {new}")
print(f"\nTOL changes (widen-only, {len(tol_changes)}):")
for aid, rid, kind, old, new in tol_changes:
    print(f"  {aid:22s} {rid:20s} {kind} {old} -> {new}")
