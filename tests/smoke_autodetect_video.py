"""Integration smoke test: upload a real-person video, enable auto-detect
(__auto__), and confirm the server keeps streaming frames instead of dying.

This reproduces the user's exact complaint ("upload video shows画面, but
enabling auto-detect stops it"). Run against a live server on :8000.
"""
import sys, os, io, time, asyncio, json, base64, urllib.request, urllib.error

sys.path.insert(0, "/Users/ching-juichang/Yoga_project_v1_workbuddy")
import cv2
import numpy as np
import websockets

SRC_PHOTO = "/Users/ching-juichang/Yoga_project_v1_workbuddy/data/uploads/01c33c2c86d74f1e91d4a4be661aaa25.jpg"
BASE = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws"
OUT_VIDEO = "/Users/ching-juichang/Yoga_project_v1_workbuddy/data/uploads/_smoke_autodetect.mp4"

def build_video():
    img = cv2.imread(SRC_PHOTO)
    h, w = img.shape[:2]
    scale = min(640 / w, 480 / h)
    nw, nh = int(w * scale), int(h * scale)
    frame = cv2.resize(img, (nw, nh))
    # pad to 640x480
    canvas = np.zeros((480, 640, 3), dtype=np.uint8)
    canvas[(480 - nh) // 2:(480 - nh) // 2 + nh, (640 - nw) // 2:(640 - nw) // 2 + nw] = frame
    writer = cv2.VideoWriter(OUT_VIDEO, cv2.VideoWriter_fourcc(*"mp4v"), 25, (640, 480))
    for i in range(120):  # ~4.8s
        # tiny horizontal jitter so frames differ but pose stays detectable
        shift = int(6 * np.sin(i / 12.0))
        m = np.roll(canvas, shift, axis=1)
        writer.write(m)
    writer.release()
    print(f"[ok] wrote {OUT_VIDEO} ({os.path.getsize(OUT_VIDEO)} bytes)")

def upload_video():
    with open(OUT_VIDEO, "rb") as f:
        data = f.read()
    boundary = "----smokeboundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="smoke.mp4"\r\n'
        f"Content-Type: video/mp4\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(BASE + "/api/upload", data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

async def run(path):
    async with websockets.connect(WS_URL) as ws:
        await ws.send(json.dumps({
            "type": "start",
            "asanaId": "__auto__",
            "source": "video",
            "path": path,
        }))
        frames = 0
        errors = 0
        detected = 0
        first_detected_id = None
        deadline = time.time() + 6.0
        while time.time() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except websockets.ConnectionClosed:
                print("[!!] connection closed by server before deadline")
                break
            msg = json.loads(raw)
            if msg.get("type") == "error":
                errors += 1
                print("[ERROR MSG]", msg.get("msg"))
            elif msg.get("type") == "frame":
                frames += 1
                fb = msg.get("feedback")
                if isinstance(fb, dict) and fb.get("detected"):
                    detected += 1
                    if first_detected_id is None:
                        first_detected_id = fb["detected"].get("id")
            elif msg.get("type") == "ready":
                pass
        print(f"[result] frames={frames} errors={errors} frames_with_detected={detected}")
        print(f"[result] first detected asana id = {first_detected_id}")
        ok = frames > 20 and errors == 0 and detected > 0
        print("PASS" if ok else "FAIL")
        return ok

if __name__ == "__main__":
    build_video()
    up = upload_video()
    print("[upload]", up)
    assert up.get("kind") == "video", up
    ok = asyncio.run(run(up["path"]))
    sys.exit(0 if ok else 1)
