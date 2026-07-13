"""Muscle-tension calibration tool (standalone, MVP).

A separate, lightweight app for *human* calibration of per-asana muscle
exertion levels. It is deliberately decoupled from the main analyzer:

  - reuses core/detector.py for pose detection
  - reads the same data/asanas.json (single source of truth for params)
  - writes adjustments to data/asanas.calibration.json (an overlay), so the
    main library is never mutated directly and changes are easy to review/rollback

IMPORTANT: a muscle `level` is expert knowledge ("how hard this muscle
*should* work in this asana") and CANNOT be derived from a single photo.
The photo is only a visual reference + overlay check; the real numbers are
entered by a teacher/expert via the sliders.
"""
from __future__ import annotations

import os
import json
import asyncio
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from core.detector import PoseDetector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ASANA_PATH = ROOT / "data" / "asanas.json"
CALIB_PATH = ROOT / "data" / "asanas.calibration.json"

# Model download happens once on first detect(); reuse the singleton.
_detector: PoseDetector | None = None


def get_detector() -> PoseDetector:
    global _detector
    if _detector is None:
        _detector = PoseDetector()
    return _detector


def _load_asanas() -> dict:
    with open(ASANA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_calib() -> dict:
    if CALIB_PATH.exists():
        try:
            return json.loads(CALIB_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_calib(data: dict) -> None:
    CALIB_PATH.parent.mkdir(parents=True, exist_ok=True)
    CALIB_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


app = FastAPI(title="Yoga Muscle Calibrator (MVP)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/asanas")
def api_asanas():
    """Current muscle levels from the main library (the 'reference' column)."""
    data = _load_asanas()
    out = []
    for a in data.get("asanas", []):
        out.append(
            {
                "id": a["id"],
                "name_zh": a.get("name_zh", a["id"]),
                "name_en": a.get("name_en", ""),
                "muscles": [
                    {
                        "id": m["id"],
                        "name_zh": m.get("name_zh", m["id"]),
                        "side": m.get("side", "both"),
                        "segment": m.get("segment", []),
                        "level": m.get("level", 0.0),
                    }
                    for m in a.get("muscles", [])
                ],
            }
        )
    return {"asanas": out}


@app.get("/api/calibration")
def api_get_calibration(asana: str | None = None):
    """Read the overlay. Whole file, or one asana if `asana` is given."""
    calib = _load_calib()
    if asana is not None:
        return {"asana_id": asana, "muscles": calib.get(asana, {})}
    return {"calibration": calib}


@app.put("/api/calibration")
async def api_put_calibration(payload: dict):
    """Merge `{asana_id, muscles:{id:level}}` into the overlay file."""
    asana_id = payload.get("asana_id")
    muscles = payload.get("muscles")
    if not asana_id or not isinstance(muscles, dict):
        raise HTTPException(400, "need {asana_id, muscles:{id:level}}")
    # basic sanity: levels in [0,1]
    clean = {}
    for mid, lvl in muscles.items():
        try:
            v = float(lvl)
        except (TypeError, ValueError):
            raise HTTPException(400, f"level for {mid} not numeric")
        clean[mid] = max(0.0, min(1.0, round(v, 3)))
    calib = _load_calib()
    calib[asana_id] = clean
    _save_calib(calib)
    return {"ok": True, "asana_id": asana_id, "muscles": clean}


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
    except Exception as e:  # model download / inference failure
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
