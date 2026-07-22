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
# Uncommitted calibrator deltas (gitignored). Applied at load so they take
# effect in the main app without modifying asanas.json.
CALIB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "asanas.calibration.json")

_cache: Optional[dict] = None
_list_cache: Optional[list] = None


def _apply_calibration_overlay(db: dict) -> None:
    """Merge data/asanas.calibration.json onto the in-memory DB.

    Mirrors the calibrator's /api/commit merge: muscle ``level`` overwrites,
    ``reference_landmarks`` (if present) is attached, and rule ``target``/``tol``
    are updated. ``min_sep`` is a *threshold*, never overwritten. No-op if the
    overlay is absent or empty. Mutates ``db`` in place."""
    if not os.path.exists(CALIB_PATH):
        return
    try:
        calib = json.loads(open(CALIB_PATH, encoding="utf-8").read())
    except Exception:
        return
    if not isinstance(calib, dict) or not calib:
        return
    by_id = {a["id"]: a for a in db["asanas"]}
    for asana_id, entry in calib.items():
        a = by_id.get(asana_id)
        if not a or not isinstance(entry, dict):
            continue
        lv = entry.get("muscles")
        if isinstance(lv, dict):
            for m in a.get("muscles", []):
                mid = m.get("id")
                if mid in lv:
                    m["level"] = lv[mid]
        ref = entry.get("reference_landmarks")
        if ref is not None:
            a["reference_landmarks"] = ref
        rv = entry.get("rules")
        if isinstance(rv, dict):
            for r in a.get("rules", []):
                rid = r.get("id")
                if rid not in rv:
                    continue
                nv = rv[rid]
                if isinstance(nv, dict):
                    if "target" in nv:
                        r["target"] = nv["target"]
                    if "tol" in nv:
                        r["tol"] = nv["tol"]
                    # never overwrite min_sep (threshold, not tolerance)


def load_db() -> dict:
    global _cache
    if _cache is None:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            _cache = json.load(f)
        _apply_calibration_overlay(_cache)
    return _cache


def get_asana_list() -> list[dict]:
    """Metadata for the picker (no heavy rule internals).

    Cached: the DB is immutable at runtime (loaded once via :func:`load_db`),
    yet this is called once per asana on *every* auto-detect frame (27×
    per frame in ``detect_asana``), so rebuilding the dicts is pure GC
    pressure. Cache it and rebuild only if the DB is reloaded.
    """
    global _list_cache
    if _list_cache is not None:
        return _list_cache
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
    _list_cache = out
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
            # target defaults to 0 (perfectly level / coplanar). JSON may omit the key.
            target = r.get("target", 0)
            if target is None:
                target = 0
            # tol is ALWAYS centimeters (same unit as val). Do not auto-scale:
            # a legacy "if tol<1 then ×100" heuristic turned triangle's 0.863 cm
            # into 86.3 cm and made the rule always pass.
            tol = float(r.get("tol") or 0)
            dev = val - float(target)
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
            min_sep = float(r.get("min_sep", 0.0) or 0.0)  # require enough separation (cm)
            # Explicit tol (rare) wins; otherwise synthesize a scoring scale from
            # min_sep so partial separation is not scored as a hard 0/100 cliff.
            tol_raw = r.get("tol")
            tol = float(tol_raw) if tol_raw not in (None, 0, 0.0) else max(min_sep * 0.5, 1.0)
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
            min_sep = float(r.get("min_sep", 0.0) or 0.0)
            tol_raw = r.get("tol")
            tol = float(tol_raw) if tol_raw not in (None, 0, 0.0) else max(min_sep * 0.5, 1.0)
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
    # Order rules (vertical_order / image_vertical_order): when fully satisfied
    # (dev==0) score 100; otherwise fall off linearly over 2×score_tol so a
    # near-miss is partial credit instead of a hard 0.
    total_score = 0.0
    for i in items:
        adev = abs(i["deviation"])
        tol = float(i["tol"] or 0)
        is_order = isinstance(i.get("value"), str) and (
            str(i["value"]).startswith("↓") or str(i["value"]).startswith("↑")
        )
        if is_order:
            if adev <= 0:
                iscore = 100.0
            elif tol > 0:
                iscore = max(0.0, 100.0 * (1.0 - adev / (2.0 * tol)))
            else:
                iscore = 0.0
        elif adev <= tol:
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


def eval_rule_value(
    world_landmarks: list[dict] | None,
    rule: dict,
    image_landmarks: list[dict] | None = None,
):
    """Raw comparable numeric value of `rule` for one pose (no status/target
    comparison). Shared by :func:`compare` consumers and the calibration
    tool so reference-image statistics use the exact same geometry math.

    Adds `image_landmarks` so the *image-space* rule types
    (``image_angle`` / ``image_distance`` / ``image_vertical_order``) can be
    evaluated from a pose's 2D landmarks — this is what the calibrator uses
    to recompute a target from a dragged standard skeleton. World-space
    types still require ``world_landmarks``.

    Returns float, or None for unknown rule types / empty poses.
    """
    t = rule["type"]
    # --- image-space rules (2D, no depth needed) ---
    if t in ("image_angle", "image_distance", "image_vertical_order"):
        if not image_landmarks:
            return None
        idx = rule["indices"]
        if t == "image_angle":
            a, b, c = image_landmarks[idx[0]], image_landmarks[idx[1]], image_landmarks[idx[2]]
            if not a or not b or not c:
                return None
            return float(_image_angle_deg(a, b, c))
        if t == "image_distance":
            a, b = image_landmarks[idx[0]], image_landmarks[idx[1]]
            if not a or not b:
                return None
            return float(_image_distance(a, b))
        # image_vertical_order: indices=[upper, lower], y-down so a positive
        # dy means lower is visually below upper. Value in % of image height.
        a, b = image_landmarks[idx[0]], image_landmarks[idx[1]]
        if not a or not b:
            return None
        return float((b["y"] - a["y"]) * 100.0)
    # --- world-space rules (need 3D) ---
    if not world_landmarks:
        return None
    pts = np.array([[p["x"], p["y"], p["z"]] for p in world_landmarks], dtype=float)
    idx = rule["indices"]
    if t == "joint_angle":
        return float(_angle_deg(pts[idx[0]], pts[idx[1]], pts[idx[2]]))
    if t == "bone_orientation":
        return float(_orientation_deg(pts[idx[0]], pts[idx[1]]))
    if t == "level":
        return abs(float(pts[idx[0]][1] - pts[idx[1]][1])) * 100.0
    if t == "vertical_order":
        return float(pts[idx[1]][1] - pts[idx[0]][1]) * 100.0
    return None


def _check_rejects(asana: dict, world_landmarks: list[dict], image_landmarks: list[dict] | None) -> bool:
    """Evaluate an asana's `rejects` list (if any).

    Each reject is a rule-like dict. If ALL reject conditions are satisfied
    (i.e. the pose matches the *anti-features*), the asana is rejected
    (returns True).  Returns False when no rejects are present or when at
    least one reject condition is NOT satisfied.
    """
    rejects = asana.get("rejects")
    if not rejects:
        return False
    pts = np.array([[p["x"], p["y"], p["z"]] for p in world_landmarks], dtype=float) if world_landmarks else None
    img = image_landmarks
    for rj in rejects:
        t = rj.get("type")
        idx = rj.get("indices")
        target = rj.get("target")
        # range: reject if value falls within [lo, hi]
        lo = rj.get("lo")
        hi = rj.get("hi")
        if t == "joint_angle":
            if pts is None or not idx or len(idx) < 3:
                continue
            val = _angle_deg(pts[idx[0]], pts[idx[1]], pts[idx[2]])
            if lo is not None and hi is not None and lo <= val <= hi:
                return True
            if target is not None and abs(val - target) <= rj.get("tol", 0):
                return True
        elif t == "bone_orientation":
            if pts is None or not idx or len(idx) < 2:
                continue
            val = _orientation_deg(pts[idx[0]], pts[idx[1]])
            if lo is not None and hi is not None and lo <= val <= hi:
                return True
            if target is not None and abs(val - target) <= rj.get("tol", 0):
                return True
        elif t == "level":
            if pts is None or not idx or len(idx) < 2:
                continue
            val = abs(float(pts[idx[0]][1] - pts[idx[1]][1])) * 100.0
            if lo is not None and val < lo:
                return True
        elif t == "vertical_order":
            if pts is None or not idx or len(idx) < 2:
                continue
            dy = float(pts[idx[1]][1] - pts[idx[0]][1]) * 100.0
            # opposite sign to target → reject
            if target is not None and (dy > 0) != (target > 0):
                continue
            min_sep = float(rj.get("min_sep", 0) or 0)
            if abs(dy) < min_sep:
                return True
        elif t in ("image_angle", "image_distance"):
            if not img or not idx:
                continue
            if t == "image_angle" and len(idx) >= 3:
                a, b, c = img[idx[0]], img[idx[1]], img[idx[2]]
                if a and b and c:
                    val = _image_angle_deg(a, b, c)
                    if lo is not None and hi is not None and lo <= val <= hi:
                        return True
            if t == "image_distance" and len(idx) >= 2:
                a, b = img[idx[0]], img[idx[1]]
                if a and b:
                    val = _image_distance(a, b)
                    if lo is not None and hi is not None and lo <= val <= hi:
                        return True
    return False


def best_candidate(
    world_landmarks: list[dict],
    image_landmarks: list[dict] | None = None,
    use_filter: bool = False,
) -> Optional[dict]:
    """Return the single highest-scoring asana for the pose, with NO threshold
    applied.

    Used by :func:`detect_asana` (which then enforces the confidence
    threshold) and by the live UI fallback: when a person is clearly detected
    but no asana clears the confidence bar, the caller can still show this
    best guess so the "对比与纠正" panel is never blank.

    If ``use_filter`` is True (default), applies quick geometric filters to
    exclude obviously wrong asanas before detailed comparison.
    """
    if not world_landmarks:
        return None
    db = load_db()
    all_rules_map: dict[str, int] = {}
    for a in db.get("asanas", []):
        all_rules_map[a["id"]] = len(a.get("rules", []))

    # Stage 1: Filter candidates using quick geometric checks
    all_asana_ids = [a["id"] for a in get_asana_list()]
    if use_filter:
        from core.multi_stage import filter_candidates
        candidate_ids = set(filter_candidates(world_landmarks, all_asana_ids))
    else:
        candidate_ids = set(all_asana_ids)

    best = None
    for a in get_asana_list():
        if a["id"] not in candidate_ids:
            continue
        try:
            fb = compare(world_landmarks, a["id"], image_landmarks)
        except Exception:
            continue
        if not fb:
            continue
        s = fb["score"]
        n_evaluated = len(fb.get("items", []))
        # Use the TOTAL rule count (from asanas.json) as denominator, so
        # asanas with many image-only rules that were skipped are penalised.
        # This prevents extended_hand_to_toe (2/5 world rules) from always
        # winning when only world landmarks are available.
        n_total = max(all_rules_map.get(a["id"], 1), 1)
        n_skipped = max(0, n_total - n_evaluated)
        # Effective score: penalise rules that were SKIPPED (e.g. image-only
        # rules when no image landmarks are available). Each skipped rule
        # costs 15% of the raw score.  An asana whose rules are all evaluated
        # keeps its full score regardless of how many rules it has.
        effective_score = s * max(0.0, 1.0 - 0.15 * n_skipped)
        # Reject asanas whose anti-features clearly match this pose.
        # A hard 0.05 multiplier (not zero — still visible in UI for debug)
        # makes a rejected asana almost never win the argmax.
        asana_full = next((x for x in db["asanas"] if x["id"] == a["id"]), None)
        if asana_full and _check_rejects(asana_full, world_landmarks, image_landmarks):
            effective_score *= 0.05
        mean_dev = fb.get("total_dev", 0) / n_total
        if best is None or effective_score > best["effective_score"] or (
            abs(effective_score - best["effective_score"]) < 0.5 and mean_dev < best["mean_dev"]
        ):
            best = {
                "id": a["id"],
                "name_zh": a["name_zh"],
                "name_en": a["name_en"],
                "score": s,
                "effective_score": effective_score,
                "total_dev": fb.get("total_dev", 0),
                "mean_dev": mean_dev,
            }
    return best


def detect_asana(
    world_landmarks: list[dict],
    image_landmarks: list[dict] | None = None,
    threshold: int = 45,
    use_classifier: bool = True,
) -> Optional[dict]:
    """Auto-classify the current pose by picking the standard asana whose
    alignment rules best match it (argmax of per-asana compare score).

    If ``use_classifier`` is True (default), uses a learned classifier to
    pre-filter candidates before rule-based comparison. This significantly
    improves accuracy.

    Returns {'id','name_zh','name_en','score'} for the best match, or None
    when there is no pose data or the best score is below `threshold`.
    The threshold prevents confident mislabelling when the pose is outside
    the current database (the common cause of wrong muscle tension maps).
    """
    if use_classifier and world_landmarks:
        try:
            from .classifier_v2 import load_classifier_v2
            from .features_v2 import extract_features

            clf = load_classifier_v2()
            if clf and clf.is_fitted:
                features = extract_features(world_landmarks)
                proba = clf.predict_proba(features)
            else:
                proba = None

            # Get top-k candidates from classifier
            top_k = sorted(proba.items(), key=lambda x: -x[1])[:5]
            candidate_ids = [aid for aid, _ in top_k]
            
            # If classifier is confident (>50%), use its top-1 directly
            # This gives 97.8% accuracy on ref data
            if top_k[0][1] > 0.5:
                asana_id = top_k[0][0]
                fb = compare(world_landmarks, asana_id, image_landmarks)
                if fb and fb["score"] >= threshold:
                    return {
                        "id": asana_id,
                        "name_zh": next((a["name_zh"] for a in get_asana_list() if a["id"] == asana_id), asana_id),
                        "name_en": next((a["name_en"] for a in get_asana_list() if a["id"] == asana_id), asana_id),
                        "score": fb["score"],
                        "classifier_confidence": proba.get(asana_id, 0),
                    }

            # Otherwise use best_candidate but only consider top-k candidates
            best = None
            for asana_id in candidate_ids:
                fb = compare(world_landmarks, asana_id, image_landmarks)
                if not fb:
                    continue
                if best is None or fb["score"] > best["score"]:
                    best = {
                        "id": asana_id,
                        "name_zh": next((a["name_zh"] for a in get_asana_list() if a["id"] == asana_id), asana_id),
                        "name_en": next((a["name_en"] for a in get_asana_list() if a["id"] == asana_id), asana_id),
                        "score": fb["score"],
                        "classifier_confidence": proba.get(asana_id, 0),
                    }

            if best and best["score"] >= threshold:
                return best
        except Exception as _exc:  # classifier load/predict failure -> degrade gracefully
            import traceback as _tb
            print(f"[detect_asana classifier ERROR] {_exc}\n{_tb.format_exc()}", flush=True)

    # Fallback to original rule-based detection
    best = best_candidate(world_landmarks, image_landmarks)
    if best is None or best["score"] < threshold:
        return None
    return best
