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


def compare(world_landmarks: list[dict], asana_id: str) -> Optional[dict]:
    asana = get_asana(asana_id)
    if asana is None or not world_landmarks:
        return None
    pts = np.array([[p["x"], p["y"], p["z"]] for p in world_landmarks], dtype=float)
    items: list[dict] = []
    for r in asana["rules"]:
        idx = r["indices"]
        t = r["type"]
        if t == "joint_angle":
            val = _angle_deg(pts[idx[0]], pts[idx[1]], pts[idx[2]])
        elif t == "bone_orientation":
            val = _orientation_deg(pts[idx[0]], pts[idx[1]])
        elif t == "level":
            val = abs(float(pts[idx[0]][1] - pts[idx[1]][1])) * 100.0  # cm
        else:
            continue
        target = r.get("target", 0)
        tol = r["tol"]
        dev = val - target
        adev = abs(dev)
        status = "ok" if adev <= tol else ("warn" if adev <= 2 * tol else "off")
        items.append(
            {
                "id": r["id"],
                "label": r["label"],
                "value": round(val, 1),
                "target": target,
                "tol": tol,
                "deviation": round(dev, 1),
                "status": status,
                "correction": r["correction"],
            }
        )
    ok = sum(1 for i in items if i["status"] == "ok")
    score = round(100 * ok / len(items)) if items else 0
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
    return {"asana_id": asana_id, "score": score, "items": items, "muscles": muscles}


def detect_asana(world_landmarks: list[dict]) -> Optional[dict]:
    """Auto-classify the current pose by picking the standard asana whose
    alignment rules best match it (argmax of per-asana compare score).

    Returns {'id','name_zh','name_en','score'} for the best match, or None
    when there is no pose data. Used so the user does not have to pick the
    target asana manually (which was the root cause of wrong tension maps).
    """
    if not world_landmarks:
        return None
    best = None
    for a in get_asana_list():
        try:
            fb = compare(world_landmarks, a["id"])
        except Exception:
            continue
        if not fb:
            continue
        s = fb["score"]
        if best is None or s > best["score"]:
            best = {
                "id": a["id"],
                "name_zh": a["name_zh"],
                "name_en": a["name_en"],
                "score": s,
            }
    return best
