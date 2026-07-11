"""Unified frame source abstraction for image / video / camera.

All sources yield numpy BGR frames (OpenCV convention) so downstream
code (detection, rendering) never cares where the pixels came from.
"""
from __future__ import annotations

import base64
from typing import Iterator

import cv2
import numpy as np


def decode_b64_frame(data: str | None) -> np.ndarray | None:
    """Decode a base64 JPEG/PNG data string (with or without data: prefix)."""
    if not data:
        return None
    if "," in data:  # strip "data:image/jpeg;base64," prefix
        data = data.split(",", 1)[1]
    raw = base64.b64decode(data)
    arr = np.frombuffer(raw, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


class FrameSource:
    """Iterates frames from a cv2.VideoCapture (video or camera)."""

    def __init__(self, cap: cv2.VideoCapture, kind: str, loop: bool = False):
        self.cap = cap
        self.kind = kind  # "video" | "camera"
        self.loop = loop

    @classmethod
    def from_video(cls, path: str, loop: bool = False) -> "FrameSource":
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {path}")
        return cls(cap, "video", loop=loop)

    @classmethod
    def from_camera(cls, idx: int = 0) -> "FrameSource":
        cap = cv2.VideoCapture(idx)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open camera index {idx}")
        return cls(cap, "camera")

    def __iter__(self) -> Iterator[np.ndarray]:
        try:
            while True:
                ok, frame = self.cap.read()
                if not ok:
                    if self.kind == "camera":
                        break
                    if self.loop:
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    break
                yield frame
        finally:
            self.cap.release()
