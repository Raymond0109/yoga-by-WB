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
from fastapi import FastAPI, UploadFile, File, WebSocket, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from core.detector import PoseDetector
from core.hand_detector import HandDetector
from core.input_source import FrameSource, decode_b64_frame
from core.landmark_smoother import LandmarkSmoother
from core.geometry_check import check_skeleton
from core.pose_compare import get_asana_list, compare, detect_asana

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB

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
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".mp4", ".mov", ".avi", ".webm", ".mkv", ".jpg", ".jpeg", ".png", ".gif", ".webp"):
        raise HTTPException(status_code=400, detail="不支持的文件类型")
    path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
    total = 0
    with open(path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                f.close()
                os.remove(path)
                raise HTTPException(status_code=413, detail=f"文件超过 {MAX_UPLOAD_BYTES // (1024*1024)} MB 限制")
            f.write(chunk)
    return {"path": path, "kind": "video" if _is_video_ext(ext) else "image"}


@app.get("/api/asanas")
def asanas():
    return get_asana_list()


def _smooth_pose(pose: dict, smooth_img: LandmarkSmoother, smooth_world: LandmarkSmoother) -> dict:
    """Apply temporal smoothing (One Euro Filter + keyframe lock) to one
    pose's image-space and world-space landmarks in place-safe copy."""
    out = dict(pose)
    if pose.get("landmarks"):
        out["landmarks"] = smooth_img.smooth(pose["landmarks"])
    if pose.get("world_landmarks"):
        out["world_landmarks"] = smooth_world.smooth(pose["world_landmarks"])
    return out


async def _send_frame(
    ws: WebSocket,
    frame: np.ndarray,
    asana_id: str | None,
    smooth_img: LandmarkSmoother,
    smooth_world: LandmarkSmoother,
    jpeg_b64: str | None = None,
) -> None:
    poses = detector.detect(frame)
    hands = hand_detector.detect(frame)
    feedback = None
    if poses:
        # smooth before any comparison / detection and before sending to UI
        poses = [_smooth_pose(poses[0], smooth_img, smooth_world)] + poses[1:]
    world = poses[0].get("world_landmarks", []) if poses else []
    image = poses[0].get("landmarks", []) if poses else []
    if asana_id and asana_id != "__auto__" and poses:
        feedback = compare(world, asana_id, image)
    elif asana_id == "__auto__" and poses:
        det = detect_asana(world, image)
        if det:
            feedback = compare(world, det["id"], image)
            feedback["detected"] = det
        else:
            feedback = {
                "asana_id": "__unknown__",
                "score": 0,
                "total_dev": 0,
                "items": [],
                "muscles": [],
                "low_score_tip": None,
                "detected": {"id": "__unknown__", "name_zh": "未识别", "name_en": "Unknown pose", "score": 0},
            }
    # When the frame came from the browser's own webcam we already have its
    # JPEG bytes; echo them back so the client draws exactly what it sent.
    jpeg = jpeg_b64 if jpeg_b64 is not None else _frame_to_jpeg(frame)
    if jpeg is None:
        return
    h, w = frame.shape[:2]
    skeleton_ok, _ = check_skeleton(world) if world else (True, [])
    await ws.send_json(
        {
            "type": "frame",
            "frame": jpeg,
            "width": w,
            "height": h,
            "poses": poses,
            "hands": hands,
            "feedback": feedback,
            "skeleton_ok": skeleton_ok,
        }
    )


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    stop_ev = asyncio.Event()
    task = None
    # client-camera mode: the browser captures its own webcam (getUserMedia)
    # and streams JPEG frames to us; we detect + compare and echo feedback.
    client_mode = False
    asana_id = None
    smooth_img_c = LandmarkSmoother()
    smooth_world_c = LandmarkSmoother()

    async def _stream(src, aid):
        # fresh smoothers per stream so smoothing state never leaks between
        # different connections / restarts
        smooth_img = LandmarkSmoother()
        smooth_world = LandmarkSmoother()
        try:
            for frame in src:
                if stop_ev.is_set():
                    break
                try:
                    await _send_frame(ws, frame, aid, smooth_img, smooth_world)
                except Exception:
                    break  # client disconnected mid-stream
                await asyncio.sleep(0.03)  # ~30fps, yield to the event loop
        except Exception as exc:  # surface source errors to the UI
            try:
                await ws.send_json({"type": "error", "msg": str(exc)})
            except Exception:
                pass
        finally:
            src.close()

    try:
        while True:
            msg = await ws.receive_json()
            mtype = msg.get("type")

            if mtype == "stop":
                stop_ev.set()
                client_mode = False
                continue

            # A frame pushed by the browser's own webcam in client-camera mode.
            if mtype == "frame" and client_mode:
                frame = decode_b64_frame(msg.get("data"))
                if frame is None:
                    continue
                try:
                    await _send_frame(
                        ws, frame, asana_id, smooth_img_c, smooth_world_c,
                        jpeg_b64=msg.get("data"),
                    )
                except Exception:
                    pass
                continue

            if mtype != "start":
                continue

            # cancel any running server-side stream before starting anew
            stop_ev.set()
            if task is not None:
                try:
                    await task
                except Exception:
                    pass
            stop_ev = asyncio.Event()
            asana_id = msg.get("asanaId")
            source = msg.get("source")

            # client-camera: no server capture needed, just flip the mode on
            if source == "client-camera":
                client_mode = True
                smooth_img_c = LandmarkSmoother()
                smooth_world_c = LandmarkSmoother()
                try:
                    await ws.send_json({"type": "ready"})
                except Exception:
                    pass
                continue

            client_mode = False
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
                        # single frame -> throwaway smoothers (no history)
                        await _send_frame(ws, frame, asana_id, LandmarkSmoother(), LandmarkSmoother())
                    continue
                else:
                    await ws.send_json({"type": "error", "msg": "unknown source"})
                    continue
            except Exception as exc:
                # Surface camera/video errors prominently so the UI is never
                # left silently empty (e.g. no webcam on the server machine).
                await ws.send_json({"type": "error", "msg": f"无法获取画面：{exc}"})
                continue
            task = asyncio.create_task(_stream(src, asana_id))
    except Exception:
        pass  # client disconnected
    finally:
        stop_ev.set()
        if task is not None and not task.done():
            try:
                await asyncio.wait_for(task, timeout=2.0)
            except Exception:
                task.cancel()
