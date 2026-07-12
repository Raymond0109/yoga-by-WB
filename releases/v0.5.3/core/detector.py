"""MediaPipe PoseLandmarker wrapper.

Outputs the 33 BlazePose landmarks in both normalized image space
(x,y in [0,1], y-down) and metric world space (origin at hip center,
y-up), plus per-point visibility. The model file is downloaded once on
first use if missing.
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
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)
MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "models", "pose_landmarker_lite.task"
)


class PoseDetector:
    def __init__(self, model_path: str = MODEL_PATH, num_poses: int = 1):
        self.model_path = model_path
        if not os.path.exists(model_path):
            self._download(model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=model_path),
            running_mode=vision.RunningMode.IMAGE,
            num_poses=num_poses,
        )
        self.landmarker = vision.PoseLandmarker.create_from_options(options)

    @staticmethod
    def _download(path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print(f"[detector] downloading pose model -> {path}")
        urllib.request.urlretrieve(MODEL_URL, path)

    def detect(self, frame_bgr: np.ndarray) -> list[dict]:
        """Run detection on one BGR frame; return list of pose dicts."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.landmarker.detect(mp_image)
        return self._serialize(result)

    @staticmethod
    def _serialize(result) -> list[dict]:
        poses: list[dict] = []
        landmarks_list = result.pose_landmarks or []
        world_list = result.pose_world_landmarks or []
        for lm_set, world_set in zip(landmarks_list, world_list):
            poses.append(
                {
                    "landmarks": [
                        {"x": p.x, "y": p.y, "z": p.z, "v": p.visibility}
                        for p in lm_set
                    ],
                    "world_landmarks": [
                        {"x": p.x, "y": p.y, "z": p.z, "v": p.visibility}
                        for p in world_set
                    ],
                }
            )
        return poses
