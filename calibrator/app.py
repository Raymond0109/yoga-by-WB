"""Muscle-tension calibration tool (standalone).

A separate, lightweight app for *human* calibration of per-asana muscle
exertion levels and standard-pose angles. Decoupled from the main analyzer:

  - reuses core/detector.py for pose detection
  - reads the same data/asanas.json (single source of truth for params)
  - reads data/ref/<id>/*.json as the "standard pose" reference skeletons
  - writes adjustments to data/asanas.calibration.json (an overlay): muscle
    levels AND an optional adjusted reference_landmarks per asana
  - /api/commit merges the overlay back into asanas.json (with a backup)

IMPORTANT: a muscle `level` and a fine-tuned pose are expert knowledge and
CANNOT be derived from a single photo. The photo/reference is only a visual
reference + overlay check; the real numbers are entered by a teacher/expert.
"""
from __future__ import annotations

import os
import json
import glob
import shutil
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from core.detector import PoseDetector
from core.muscle_catalog import CATALOG, ORDER

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ASANA_PATH = ROOT / "data" / "asanas.json"
CALIB_PATH = ROOT / "data" / "asanas.calibration.json"
REF_DIR = ROOT / "data" / "ref"

_detector: PoseDetector | None = None


def get_detector() -> PoseDetector:
    global _detector
    if _detector is None:
        _detector = PoseDetector()
    return _detector


def _load_asanas() -> dict:
    return json.loads(ASANA_PATH.read_text(encoding="utf-8"))


def _load_calib() -> dict:
    if CALIB_PATH.exists():
        try:
            return json.loads(CALIB_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_calib(data: dict) -> None:
    CALIB_PATH.parent.mkdir(parents=True, exist_ok=True)
    CALIB_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _project_world_to_image(world: list[dict]) -> list[dict]:
    """Orthographic projection of world landmarks to image-normalized [0,1].

    No camera intrinsics are available, so we use a simple bbox-normalized
    orthographic map (x right, y up). Good enough to draw a comparable pose
    diagram and to edit joint angles.
    """
    pts = [(w["x"], w["y"], w.get("v", 1.0)) for w in world if w.get("v", 0) > 0.1]
    if not pts:
        return [{"x": 0.5, "y": 0.5, "v": 0.0} for _ in world]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    sx = (maxx - minx) or 1.0
    sy = (maxy - miny) or 1.0
    out = []
    for w in world:
        if w.get("v", 0) > 0.1:
            x = (w["x"] - minx) / sx
            y = (maxy - w["y"]) / sy  # flip: image y is down
        else:
            x = 0.5
            y = 0.5
        out.append({"x": round(x, 5), "y": round(y, 5), "v": w.get("v", 0.0)})
    return out


def _best_ref(asana_id: str):
    """Return (image_landmarks, world_landmarks, filename) for the best ref frame."""
    d = REF_DIR / asana_id
    if not d.exists():
        return None
    files = sorted(glob.glob(str(d / "ref_*.json")))
    best = None
    best_score = -1.0
    for f in files:
        try:
            data = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, list) or len(data) < 33:
            continue
        score = sum(p.get("v", 0) for p in data[:33])
        if score > best_score:
            best_score = score
            best = (data[:33], Path(f).name)
    if best is None:
        return None
    world, fname = best
    return _project_world_to_image(world), world, fname


app = FastAPI(title="Yoga Muscle Calibrator")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/asanas")
def api_asanas():
    """Full current library data per asana (muscles + rules + metadata)."""
    data = _load_asanas()
    out = []
    for a in data.get("asanas", []):
        out.append({
            "id": a["id"],
            "name_zh": a.get("name_zh", a["id"]),
            "name_en": a.get("name_en", ""),
            "aliases": a.get("aliases", []),
            "benefits": a.get("benefits", []),
            "cautions": a.get("cautions", []),
            "details": a.get("details", ""),
            "rules": [
                {
                    "id": r.get("id"),
                    "type": r.get("type"),
                    "indices": r.get("indices"),
                    "target": r.get("target"),
                    "tol": r.get("tol"),
                    "label": r.get("label", ""),
                    "correction": r.get("correction", ""),
                }
                for r in a.get("rules", [])
            ],
            "muscles": [
                {
                    "id": m["id"],
                    "name_zh": m.get("name_zh", m["id"]),
                    "side": m.get("side", "both"),
                    "segment": m.get("segment"),
                    "special": m.get("special"),
                    "face": m.get("face"),
                    "width": m.get("width"),
                    "level": m.get("level", 0.0),
                }
                for m in a.get("muscles", [])
            ],
        })
    return {"asanas": out}


@app.get("/api/reference")
def api_reference(asana: str, file: str | None = None):
    """Standard-pose reference skeleton for an asana.

    Returns the projected image landmarks + raw world landmarks of the best
    (or chosen) reference frame, plus the list of available frames for the
    picker. Returns empty when the asana has no reference data.
    """
    d = REF_DIR / asana
    available = []
    if d.exists():
        available = sorted(Path(f).name for f in glob.glob(str(d / "ref_*.json")))
    if not available:
        return {"asana": asana, "available": [], "landmarks": None,
                "world_landmarks": None, "source": None}
    fname = file if (file and file in available) else available[0]
    try:
        world = json.loads((d / fname).read_text(encoding="utf-8"))
    except Exception:
        return {"asana": asana, "available": available, "landmarks": None,
                "world_landmarks": None, "source": None}
    if not isinstance(world, list) or len(world) < 33:
        return {"asana": asana, "available": available, "landmarks": None,
                "world_landmarks": None, "source": None}
    world = world[:33]
    return {
        "asana": asana,
        "available": available,
        "landmarks": _project_world_to_image(world),
        "world_landmarks": world,
        "source": fname,
    }


@app.get("/api/calibration")
def api_get_calibration(asana: str | None = None):
    """Read the overlay. Whole file, or one asana if `asana` is given."""
    calib = _load_calib()
    if asana is not None:
        return {"asana_id": asana, "muscles": calib.get(asana, {}).get("muscles", {}),
                "reference_landmarks": calib.get(asana, {}).get("reference_landmarks")}
    return {"calibration": calib}


@app.put("/api/calibration")
async def api_put_calibration(payload: dict):
    """Merge `{asana_id, muscles:{id:level}, reference_landmarks?:[...]}`."""
    asana_id = payload.get("asana_id")
    muscles = payload.get("muscles")
    if not asana_id or not isinstance(muscles, dict):
        raise HTTPException(400, "need {asana_id, muscles:{id:level}}")
    clean = {}
    for mid, lvl in muscles.items():
        try:
            v = float(lvl)
        except (TypeError, ValueError):
            raise HTTPException(400, f"level for {mid} not numeric")
        clean[mid] = max(0.0, min(1.0, round(v, 3)))
    calib = _load_calib()
    entry = calib.get(asana_id, {})
    entry["muscles"] = clean
    ref = payload.get("reference_landmarks")
    if ref is not None:
        if not isinstance(ref, list) or len(ref) != 33:
            raise HTTPException(400, "reference_landmarks must be 33 points")
        entry["reference_landmarks"] = ref
    calib[asana_id] = entry
    _save_calib(calib)
    return {"ok": True, "asana_id": asana_id, "muscles": clean,
            "has_reference": entry.get("reference_landmarks") is not None}


@app.post("/api/commit")
async def api_commit():
    """Merge the whole calibration overlay back into asanas.json.

    Muscle levels overwrite asana.muscles[].level; reference_landmarks (if
    present) are written as asana.reference_landmarks. A timestamped backup of
    asanas.json is kept next to it before the write.
    """
    calib = _load_calib()
    if not calib:
        raise HTTPException(400, "no calibration overlay to commit")
    data = _load_asanas()
    by_id = {a["id"]: a for a in data["asanas"]}
    applied_muscles = 0
    applied_refs = 0
    for asana_id, entry in calib.items():
        a = by_id.get(asana_id)
        if not a:
            continue
        lv = entry.get("muscles")
        if lv:
            for m in a.get("muscles", []):
                if m["id"] in lv:
                    m["level"] = lv[m["id"]]
                    applied_muscles += 1
        ref = entry.get("reference_landmarks")
        if ref:
            a["reference_landmarks"] = ref
            applied_refs += 1
    # backup then write
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = ASANA_PATH.with_suffix(f".json.bak_{ts}")
    shutil.copy2(ASANA_PATH, backup)
    ASANA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "backup": backup.name, "muscles": applied_muscles,
            "references": applied_refs}


@app.post("/api/detect")
async def api_detect(file: UploadFile = File(...)):
    """Detect pose in an uploaded image; return landmarks for overlay drawing."""
    content = await file.read()
    if not content:
        raise HTTPException(400, "empty upload")
    arr = np.frombuffer(content, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(400, "cannot decode image (not jpg/png?)")
    h, w = frame.shape[:2]
    try:
        poses = get_detector().detect(frame)
    except Exception as e:
        raise HTTPException(500, f"detection failed: {e}")
    if not poses:
        return {"width": w, "height": h, "landmarks": None}
    pose = poses[0]
    return {
        "width": w,
        "height": h,
        "landmarks": pose["landmarks"],
        "world_landmarks": pose["world_landmarks"],
    }


app.mount("/", StaticFiles(directory=str(HERE / "static"), html=True), name="static")
