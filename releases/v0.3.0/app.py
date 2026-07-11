"""FastAPI entry point.

Serves the frontend, accepts uploaded image/video files, and streams
detected frames + 33-point pose landmarks to the browser over WebSocket.
Detection runs server-side (OpenCV captures camera natively, avoiding
browser getUserMedia/HTTPS requirements).
"""
from __future__ import annotations

import asyncio
import base64
import os
import uuid

import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, WebSocket
from fastapi.responses import FileResponse

from core.detector import PoseDetector
from core.hand_detector import HandDetector
from core.input_source import FrameSource, decode_b64_frame
from core.pose_compare import get_asana_list, compare

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI()
detector = PoseDetector()
hand_detector = HandDetector()


def _frame_to_jpeg(frame: np.ndarray) -> str | None:
    ok, buf = cv2.imencode(".jpg", frame)
    return base64.b64encode(buf).decode("ascii") if ok else None


def _is_video_ext(ext: str) -> bool:
    return ext.lower() in (".mp4", ".mov", ".avi", ".webm", ".mkv")


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1]
    path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
    with open(path, "wb") as f:
        f.write(await file.read())
    return {"path": path, "kind": "video" if _is_video_ext(ext) else "image"}


@app.get("/api/asanas")
def asanas():
    return get_asana_list()


async def _send_frame(ws: WebSocket, frame: np.ndarray, asana_id: str | None) -> None:
    poses = detector.detect(frame)
    hands = hand_detector.detect(frame)
    feedback = None
    if asana_id and poses:
        feedback = compare(poses[0].get("world_landmarks", []), asana_id)
    jpeg = _frame_to_jpeg(frame)
    if jpeg is None:
        return
    h, w = frame.shape[:2]
    await ws.send_json(
        {
            "type": "frame",
            "frame": jpeg,
            "width": w,
            "height": h,
            "poses": poses,
            "hands": hands,
            "feedback": feedback,
        }
    )


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("type") != "start":
                continue
            source = msg.get("source")
            asana_id = msg.get("asanaId")
            try:
                if source == "camera":
                    src = FrameSource.from_camera(0)
                elif source == "video":
                    src = FrameSource.from_video(msg["path"])
                elif source == "image":
                    frame = decode_b64_frame(msg.get("data"))
                    if frame is None and msg.get("path"):
                        frame = cv2.imread(msg["path"])
                    if frame is not None:
                        await _send_frame(ws, frame, asana_id)
                    continue
                else:
                    await ws.send_json({"type": "error", "msg": "unknown source"})
                    continue

                for frame in src:
                    await _send_frame(ws, frame, asana_id)
                    await asyncio.sleep(0)  # yield to event loop
            except Exception as exc:  # surface source errors to the UI
                await ws.send_json({"type": "error", "msg": str(exc)})
    except Exception:
        pass  # client disconnected
