"""Feature extraction for pose classification.

Extracts geometric features from 33 MediaPipe world landmarks:
- Joint angles (3-point combinations)
- Bone orientation angles
- Relative position features
- Distance ratios

Total feature vector: ~50 dimensions
"""

from __future__ import annotations
import numpy as np
from typing import List, Tuple


def _angle_between_vectors(v1: np.ndarray, v2: np.ndarray) -> float:
    """Angle between two vectors in degrees [0, 180]."""
    cos_a = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9)
    return np.degrees(np.arccos(np.clip(cos_a, -1, 1)))


def _angle_to_vertical(v: np.ndarray) -> float:
    """Angle of vector to vertical axis (y-up), folded to [0, 90]."""
    up = np.array([0.0, 1.0, 0.0])
    cos_a = np.dot(v, up) / (np.linalg.norm(v) + 1e-9)
    theta = np.degrees(np.arccos(np.clip(cos_a, -1, 1)))
    return min(theta, 180.0 - theta)


def _joint_angle(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
    """Angle at p2 formed by p1-p2-p3."""
    v1 = p1 - p2
    v2 = p3 - p2
    return _angle_between_vectors(v1, v2)


def extract_features(world_landmarks: list[dict]) -> np.ndarray:
    """Extract feature vector from 33 world landmarks.

    Returns:
        Feature vector of shape (n_features,)
    """
    pts = np.array([[p["x"], p["y"], p["z"]] for p in world_landmarks], dtype=float)

    features = []

    # ── Key landmark indices ──
    # 0: nose, 11/12: shoulders, 13/14: elbows, 15/16: wrists
    # 23/24: hips, 25/26: knees, 27/28: ankles

    # ── Joint angles ──
    # Elbows
    features.append(_joint_angle(pts[11], pts[13], pts[15]))  # left elbow
    features.append(_joint_angle(pts[12], pts[14], pts[16]))  # right elbow

    # Shoulders (using hip as reference)
    features.append(_joint_angle(pts[23], pts[11], pts[13]))  # left shoulder
    features.append(_joint_angle(pts[24], pts[12], pts[14]))  # right shoulder

    # Knees
    features.append(_joint_angle(pts[23], pts[25], pts[27]))  # left knee
    features.append(_joint_angle(pts[24], pts[26], pts[28]))  # right knee

    # Hips (using shoulder and knee)
    features.append(_joint_angle(pts[11], pts[23], pts[25]))  # left hip
    features.append(_joint_angle(pts[12], pts[24], pts[26]))  # right hip

    # ── Bone orientations to vertical ──
    # Upper arms
    features.append(_angle_to_vertical(pts[13] - pts[11]))  # left upper arm
    features.append(_angle_to_vertical(pts[14] - pts[12]))  # right upper arm

    # Lower arms
    features.append(_angle_to_vertical(pts[15] - pts[13]))  # left lower arm
    features.append(_angle_to_vertical(pts[16] - pts[14]))  # right lower arm

    # Torso (shoulder to hip)
    features.append(_angle_to_vertical(pts[23] - pts[11]))  # left torso
    features.append(_angle_to_vertical(pts[24] - pts[12]))  # right torso

    # Upper legs
    features.append(_angle_to_vertical(pts[25] - pts[23]))  # left upper leg
    features.append(_angle_to_vertical(pts[26] - pts[24]))  # right upper leg

    # Lower legs
    features.append(_angle_to_vertical(pts[27] - pts[25]))  # left lower leg
    features.append(_angle_to_vertical(pts[28] - pts[26]))  # right lower leg

    # ── Relative position features ──
    # Shoulder width (for normalization)
    shoulder_width = np.linalg.norm(pts[12] - pts[11]) + 1e-9

    # Hip width
    hip_width = np.linalg.norm(pts[24] - pts[23])
    features.append(hip_width / shoulder_width)

    # Head height relative to hips
    head_y = pts[0][1]
    hip_y = (pts[23][1] + pts[24][1]) / 2
    features.append((head_y - hip_y) / shoulder_width)

    # Ankle height relative to hips
    ankle_y = (pts[27][1] + pts[28][1]) / 2
    features.append((ankle_y - hip_y) / shoulder_width)

    # Wrist height relative to shoulders
    wrist_y = (pts[15][1] + pts[16][1]) / 2
    shoulder_y = (pts[11][1] + pts[12][1]) / 2
    features.append((wrist_y - shoulder_y) / shoulder_width)

    # ── Symmetry features ──
    # Left vs right elbow angle difference
    features.append(abs(_joint_angle(pts[11], pts[13], pts[15]) -
                       _joint_angle(pts[12], pts[14], pts[16])))

    # Left vs right knee angle difference
    features.append(abs(_joint_angle(pts[23], pts[25], pts[27]) -
                       _joint_angle(pts[24], pts[26], pts[28])))

    # ── Body center features ──
    # Center of mass (average of key points)
    com = (pts[11] + pts[12] + pts[23] + pts[24]) / 4
    features.append(com[1] / shoulder_width)  # vertical position

    # ── Forward/backward lean ──
    # Nose relative to hip center in z direction
    nose_z = pts[0][2]
    hip_z = (pts[23][2] + pts[24][2]) / 2
    features.append((nose_z - hip_z) / shoulder_width)

    # ── Arm spread ──
    # Distance between wrists relative to shoulder width
    wrist_dist = np.linalg.norm(pts[16] - pts[15])
    features.append(wrist_dist / shoulder_width)

    # ── Leg spread ──
    ankle_dist = np.linalg.norm(pts[28] - pts[27])
    features.append(ankle_dist / shoulder_width)

    return np.array(features, dtype=np.float32)


def get_feature_names() -> List[str]:
    """Return human-readable feature names."""
    return [
        "elbow_angle_l", "elbow_angle_r",
        "shoulder_angle_l", "shoulder_angle_r",
        "knee_angle_l", "knee_angle_r",
        "hip_angle_l", "hip_angle_r",
        "upper_arm_vert_l", "upper_arm_vert_r",
        "lower_arm_vert_l", "lower_arm_vert_r",
        "torso_vert_l", "torso_vert_r",
        "upper_leg_vert_l", "upper_leg_vert_r",
        "lower_leg_vert_l", "lower_leg_vert_r",
        "hip_width_ratio",
        "head_height_rel",
        "ankle_height_rel",
        "wrist_height_rel",
        "elbow_symmetry",
        "knee_symmetry",
        "com_height",
        "forward_lean",
        "arm_spread",
        "leg_spread",
    ]
