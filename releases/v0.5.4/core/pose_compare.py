"""Standard-asana comparison / correction engine.

Loads data/asanas.json and, given a detected pose's 33 MediaPipe
*world* landmarks (metric 3D, origin at hip centre, y-up — which makes
angles viewpoint-invariant), evaluates the selected asana's alignment
rules and returns per-rule status + deviation + correction cue, plus a
live muscle-engagement map.
"""
from __future__ import annotations

import json
import os
from typing import Optional

import numpy as np

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "asanas.json")

_cache: Optional[dict] = None


def load_db() -> dict:
    global _cache
    if _cache is None:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


def get_asana_list() -> list[dict]:
    """Metadata for the picker (no heavy rule internals)."""
    out = []
    for a in load_db()["asanas"]:
        out.append(
            {
                "id": a["id"],
                "name_en": a["name_en"],
                "name_sanskrit": a["name_sanskrit"],
                "name_zh": a["name_zh"],
                "category": a["category"],
                "difficulty": a["difficulty"],
                "benefits": a["benefits"],
                "aliases": a.get("aliases", []),
                "cautions": a.get("cautions", []),
                "details": a.get("details", []),
                "ref_url": a["ref_url"],
                "muscles": a.get("muscles", []),
            }
        )
    return out


def get_asana(asana_id: str) -> Optional[dict]:
    for a in load_db()["asanas"]:
        if a["id"] == asana_id:
            return a
    return None


def _angle_deg(p1, p2, p3) -> float:
    v1 = p1 - p2
    v2 = p3 - p2
    denom = (np.linalg.norm(v1) * np.linalg.norm(v2)) + 1e-9
    c = float(np.clip(np.dot(v1, v2) / denom, -1.0, 1.0))
    return float(np.degrees(np.arccos(c)))


def _orientation_deg(p1, p2) -> float:
    """Angle of bone p1->p2 to the vertical axis, folded to [0,90]
    (0 = vertical, 90 = horizontal) regardless of direction."""
    v = p2 - p1
    up = np.array([0.0, 1.0, 0.0])
    c = float(np.clip(np.dot(v, up) / (np.linalg.norm(v) + 1e-9), -1.0, 1.0))
    theta = float(np.degrees(np.arccos(c)))
    return min(theta, 180.0 - theta)


def _image_angle_deg(p1, p2, p3) -> float:
    """Angle at p2 formed by p1-p2-p3 in normalized image space (x,y)."""
    v1 = np.array([p1["x"] - p2["x"], p1["y"] - p2["y"]])
    v2 = np.array([p3["x"] - p2["x"], p3["y"] - p2["y"]])
    denom = (np.linalg.norm(v1) * np.linalg.norm(v2)) + 1e-9
    c = float(np.clip(np.dot(v1, v2) / denom, -1.0, 1.0))
    return float(np.degrees(np.arccos(c)))


def _image_distance(p1, p2) -> float:
    """Euclidean distance between two normalized image points."""
    return float(np.hypot(p1["x"] - p2["x"], p1["y"] - p2["y"]))


def compare(
    world_landmarks: list[dict],
    asana_id: str,
    image_landmarks: list[dict] | None = None,
) -> Optional[dict]:
    asana = get_asana(asana_id)
    if asana is None or not world_landmarks:
        return None
    pts = np.array([[p["x"], p["y"], p["z"]] for p in world_landmarks], dtype=float)
    items: list[dict] = []
    for r in asana["rules"]:
        idx = r["indices"]
        t = r["type"]
        unit = "°"
        if t == "joint_angle":
            val = _angle_deg(pts[idx[0]], pts[idx[1]], pts[idx[2]])
            target = r.get("target", 0)
            tol = r["tol"]
            dev = val - target
            adev = abs(dev)
            status = "ok" if adev <= tol else ("warn" if adev <= 2 * tol else "off")
        elif t == "bone_orientation":
            val = _orientation_deg(pts[idx[0]], pts[idx[1]])
            target = r.get("target", 0)
            tol = r["tol"]
            dev = val - target
            adev = abs(dev)
            status = "ok" if adev <= tol else ("warn" if adev <= 2 * tol else "off")
        elif t == "level":
            val = abs(float(pts[idx[0]][1] - pts[idx[1]][1])) * 100.0  # cm
            unit = "cm"
            target = r.get("target", 0)
            # Tolerance is specified in centimeters to match the value unit.
            tol = r["tol"] * 100.0 if r.get("tol", 0) < 1.0 else r["tol"]
            dev = val - target
            adev = abs(dev)
            status = "ok" if adev <= tol else ("warn" if adev <= 2 * tol else "off")
        elif t == "vertical_order":
            # Discriminates inversions/arm-balances from standing poses.
            # indices = [lower, upper]; world y-up. +1 => lower below upper
            # (e.g. handstand: wrist below shoulder, foot above hip); -1 => lower
            # above upper (e.g. tree: wrist above shoulder). value = signed
            # separation in cm (↑ above / ↓ below), target = expected direction.
            dy = float(pts[idx[1]][1] - pts[idx[0]][1]) * 100.0  # cm
            target = r.get("target", 1)
            min_sep = r.get("min_sep", 0.0)  # require enough separation (cm)
            tol = r.get("tol", 0.0)
            unit = ""
            ok_sign = (dy > 0) == (target > 0)
            sep = abs(dy)
            separated = sep >= min_sep
            status = "ok" if (ok_sign and separated) else ("warn" if separated else "off")
            val = f"{'↓' if dy >= 0 else '↑'}{sep:.0f}cm"
            target = f"{'↓' if target > 0 else '↑'}"
            # deviation = distance to the *satisfied* condition, so an unsatisfied
            # rule (wrong side, or not separated enough) is penalised rather than
            # credited when the physical gap happens to be ~0.
            if ok_sign and separated:
                dev = 0.0
            elif ok_sign:
                dev = max(0.0, min_sep - sep)
            else:
                dev = sep + min_sep
        elif t == "image_angle":
            # Image-space joint angle (profile/foreshortened poses where world
            # landmarks are unreliable). Normalized coordinates, y-down.
            if not image_landmarks:
                continue
            a, b, c = image_landmarks[idx[0]], image_landmarks[idx[1]], image_landmarks[idx[2]]
            if not a or not b or not c:
                continue
            val = _image_angle_deg(a, b, c)
            target = r.get("target", 0)
            tol = r["tol"]
            dev = val - target
            adev = abs(dev)
            status = "ok" if adev <= tol else ("warn" if adev <= 2 * tol else "off")
        elif t == "image_distance":
            # Normalized Euclidean distance in the image (0-1).
            if not image_landmarks:
                continue
            a, b = image_landmarks[idx[0]], image_landmarks[idx[1]]
            if not a or not b:
                continue
            val = _image_distance(a, b)
            target = r.get("target", 0)
            tol = r["tol"]
            dev = val - target
            adev = abs(dev)
            status = "ok" if adev <= tol else ("warn" if adev <= 2 * tol else "off")
            unit = ""
        elif t == "image_vertical_order":
            # Image-space relative y-position. indices=[upper,lower] with
            # y-down, so positive dy means lower is visually below upper.
            if not image_landmarks:
                continue
            a, b = image_landmarks[idx[0]], image_landmarks[idx[1]]
            if not a or not b:
                continue
            dy = (b["y"] - a["y"]) * 100.0  # percent of image height
            target = r.get("target", 1)
            min_sep = r.get("min_sep", 0.0)
            tol = r.get("tol", 0.0)
            unit = ""
            ok_sign = (dy > 0) == (target > 0)
            sep = abs(dy)
            separated = sep >= min_sep
            status = "ok" if (ok_sign and separated) else ("warn" if separated else "off")
            val = f"{'↓' if dy >= 0 else '↑'}{sep:.0f}%"
            target = f"{'↓' if target > 0 else '↑'}"
            if ok_sign and separated:
                dev = 0.0
            elif ok_sign:
                dev = max(0.0, min_sep - sep)
            else:
                dev = sep + min_sep
        else:
            continue
        items.append(
            {
                "id": r["id"],
                "label": r["label"],
                "value": round(val, 1) if isinstance(val, (int, float)) else val,
                "target": target,
                "tol": tol,
                "deviation": round(dev, 1),
                "status": status,
                "unit": unit,
                "correction": r["correction"],
            }
        )
    # Continuous per-rule score (replaces the old binary ok-count):
    #   100 within tolerance -> linearly to 0 across the warn zone
    #   (tol .. 2*tol) -> 0 beyond. The overall score then reflects *how
    #   close* the pose is, not just pass/fail, giving smoother muscle
    #   animation and a more honest grade. `status` (ok/warn/off) is kept
    #   for the severity colouring in the UI.
    total_score = 0.0
    for i in items:
        adev = abs(i["deviation"])
        tol = i["tol"]
        if adev <= tol:
            iscore = 100.0
        elif tol > 0 and adev <= 2 * tol:
            iscore = 100.0 * (1.0 - (adev - tol) / tol)
        else:
            iscore = 0.0
        i["item_score"] = round(iscore, 1)
        total_score += iscore
    score = round(total_score / len(items)) if items else 0
    # Sum of absolute per-rule deviations. Used as a tiebreaker in
    # detect_asana: when two asanas both score 100 on an input, the one
    # whose pose sits closest to its own targets (smaller total_dev) is the
    # better match. This resolves argmax collisions between geometrically
    # similar poses (e.g. gate vs cobra, low_lunge vs extended_hand_to_toe)
    # without hand-tuning every collider's rules.
    total_dev = round(sum(abs(i["deviation"]) for i in items), 1)
    # Correction ordering (Item 5): surface the biggest problems first so the
    # UI lists the most important fixes at the top. `total_dev` is a sum, so
    # this reordering never changes scoring or the detect_asana tiebreaker.
    items.sort(key=lambda i: abs(i["deviation"]), reverse=True)
    # Low-score tip (Item 5): when the overall pose is poor (<60), point the
    # user at the single worst rule's correction instead of dumping everything.
    low_score_tip = None
    if score < 60 and items:
        worst = items[0]
        low_score_tip = f"先纠正「{worst['label']}」：{worst['correction']}"
    muscles = []
    for m in asana.get("muscles", []):
        base = m["level"]
        muscles.append(
            {
                "id": m["id"],
                "name_zh": m["name_zh"],
                "segment": m["segment"],
                "side": m.get("side", "center"),
                "level": base,
                "live": round(base * (0.4 + 0.6 * score / 100.0), 2),
            }
        )
    return {"asana_id": asana_id, "score": score, "total_dev": total_dev, "items": items, "muscles": muscles, "low_score_tip": low_score_tip}


def eval_rule_value(world_landmarks: list[dict], rule: dict):
    """Raw comparable numeric value of `rule` for one pose (no status/target
    comparison). Shared by :func:`compare` consumers and the calibration
    tool so reference-image statistics use the exact same geometry math.

    Returns float, or None for unknown rule types / empty poses.
    """
    if not world_landmarks:
        return None
    pts = np.array([[p["x"], p["y"], p["z"]] for p in world_landmarks], dtype=float)
    idx = rule["indices"]
    t = rule["type"]
    if t == "joint_angle":
        return float(_angle_deg(pts[idx[0]], pts[idx[1]], pts[idx[2]]))
    if t == "bone_orientation":
        return float(_orientation_deg(pts[idx[0]], pts[idx[1]]))
    if t == "level":
        return abs(float(pts[idx[0]][1] - pts[idx[1]][1])) * 100.0
    if t == "vertical_order":
        return float(pts[idx[1]][1] - pts[idx[0]][1]) * 100.0
    return None


def detect_asana(
    world_landmarks: list[dict],
    image_landmarks: list[dict] | None = None,
    threshold: int = 45,
) -> Optional[dict]:
    """Auto-classify the current pose by picking the standard asana whose
    alignment rules best match it (argmax of per-asana compare score).

    Returns {'id','name_zh','name_en','score'} for the best match, or None
    when there is no pose data or the best score is below `threshold`.
    The threshold prevents confident mislabelling when the pose is outside
    the current database (the common cause of wrong muscle tension maps).
    """
    if not world_landmarks:
        return None
    best = None
    for a in get_asana_list():
        try:
            fb = compare(world_landmarks, a["id"], image_landmarks)
        except Exception:
            continue
        if not fb:
            continue
        s = fb["score"]
        dev = fb.get("total_dev", 0)
        # Highest score wins; on a tie (e.g. two poses both at 100%), prefer
        # the asana whose landmarks sit closest to its own rule targets
        # (smaller total deviation) — the better geometric fit. This resolves
        # argmax collisions between similar poses (gate vs cobra,
        # low_lunge vs extended_hand_to_toe, side_angle vs wheel) without
        # hand-tuning every collider's rules.
        if best is None or s > best["score"] or (s == best["score"] and dev < best["total_dev"]):
            best = {
                "id": a["id"],
                "name_zh": a["name_zh"],
                "name_en": a["name_en"],
                "score": s,
                "total_dev": dev,
            }
    if best is None or best["score"] < threshold:
        return None
    return best
