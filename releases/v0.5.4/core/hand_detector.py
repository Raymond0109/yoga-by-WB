"""MediaPipe HandLandmarker wrapper.

Outputs up to 2 hands, each with 21 landmarks in normalized image
space (x, y in [0, 1], y-down) plus handedness label and score.
The model file is downloaded once on first use if missing.

Note: HandLandmarker does not emit per-point visibility (unlike Pose),
so every hand landmark is reported with v = 1.0.
"""
from __future__ import annotations

import os
import urllib.request

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)
MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "models", "hand_landmarker.task"
)

# Canonical 21-point hand topology (mirrors legacy HAND_CONNECTIONS).
# Landmark indices: 0 wrist; 1-4 thumb; 5-8 index; 9-12 middle;
# 13-16 ring; 17-20 pinky.
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # index
    (5, 9), (9, 10), (10, 11), (11, 12),    # middle
    (9, 13), (13, 14), (14, 15), (15, 16),  # ring
    (13, 17), (17, 18), (18, 19), (19, 20),  # pinky
    (0, 17),                                   # palm base
]


class HandDetector:
    def __init__(self, model_path: str = MODEL_PATH, num_hands: int = 2):
        self.model_path = model_path
        if not os.path.exists(model_path):
            self._download(model_path)
        options = vision.HandLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.IMAGE,
            num_hands=num_hands,
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)

    @staticmethod
    def _download(path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print(f"[hand_detector] downloading hand model -> {path}")
        urllib.request.urlretrieve(MODEL_URL, path)

    def detect(self, frame_bgr: np.ndarray) -> list[dict]:
        """Run detection on one BGR frame; return list of hand dicts."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect(mp_image)
        return self._serialize(result)

    @staticmethod
    def _serialize(result) -> list[dict]:
        hands: list[dict] = []
        lm_list = result.hand_landmarks or []
        handed_list = getattr(result, "handedness", None) or getattr(
            result, "handednesses", None
        ) or []
        for lm_set, handed in zip(lm_list, handed_list):
            top = handed[0] if handed else None
            hands.append(
                {
                    "handedness": top.category_name if top else "Unknown",
                    "score": float(top.score) if top else 0.0,
                    "landmarks": [
                        {"x": p.x, "y": p.y, "z": p.z, "v": 1.0} for p in lm_set
                    ],
                }
            )
        return hands
