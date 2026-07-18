"""Enhanced feature extraction with more discriminative features."""

from __future__ import annotations
import numpy as np
from typing import List


def _angle_between_vectors(v1: np.ndarray, v2: np.ndarray) -> float:
    cos_a = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9)
    return np.degrees(np.arccos(np.clip(cos_a, -1, 1)))


def _angle_to_vertical(v: np.ndarray) -> float:
    up = np.array([0.0, 1.0, 0.0])
    cos_a = np.dot(v, up) / (np.linalg.norm(v) + 1e-9)
    theta = np.degrees(np.arccos(np.clip(cos_a, -1, 1)))
    return min(theta, 180.0 - theta)


def _joint_angle(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
    v1 = p1 - p2
    v2 = p3 - p2
    return _angle_between_vectors(v1, v2)


def extract_features(world_landmarks: list[dict]) -> np.ndarray:
    """Extract enhanced feature vector from 33 world landmarks.
    
    Returns ~45 features including:
    - Original 28 features (joint angles, bone orientations, positions)
    - Additional cross-features and ratios
    """
    pts = np.array([[p["x"], p["y"], p["z"]] for p in world_landmarks], dtype=float)
    features = []

    # ── Joint angles ──
    elbow_l = _joint_angle(pts[11], pts[13], pts[15])
    elbow_r = _joint_angle(pts[12], pts[14], pts[16])
    shoulder_l = _joint_angle(pts[23], pts[11], pts[13])
    shoulder_r = _joint_angle(pts[24], pts[12], pts[14])
    knee_l = _joint_angle(pts[23], pts[25], pts[27])
    knee_r = _joint_angle(pts[24], pts[26], pts[28])
    hip_l = _joint_angle(pts[11], pts[23], pts[25])
    hip_r = _joint_angle(pts[12], pts[24], pts[26])

    features.extend([elbow_l, elbow_r, shoulder_l, shoulder_r,
                    knee_l, knee_r, hip_l, hip_r])

    # ── Bone orientations to vertical ──
    upper_arm_vert_l = _angle_to_vertical(pts[13] - pts[11])
    upper_arm_vert_r = _angle_to_vertical(pts[14] - pts[12])
    lower_arm_vert_l = _angle_to_vertical(pts[15] - pts[13])
    lower_arm_vert_r = _angle_to_vertical(pts[16] - pts[14])
    torso_vert_l = _angle_to_vertical(pts[23] - pts[11])
    torso_vert_r = _angle_to_vertical(pts[24] - pts[12])
    upper_leg_vert_l = _angle_to_vertical(pts[25] - pts[23])
    upper_leg_vert_r = _angle_to_vertical(pts[26] - pts[24])
    lower_leg_vert_l = _angle_to_vertical(pts[27] - pts[25])
    lower_leg_vert_r = _angle_to_vertical(pts[28] - pts[26])

    features.extend([upper_arm_vert_l, upper_arm_vert_r,
                    lower_arm_vert_l, lower_arm_vert_r,
                    torso_vert_l, torso_vert_r,
                    upper_leg_vert_l, upper_leg_vert_r,
                    lower_leg_vert_l, lower_leg_vert_r])

    # ── Relative positions ──
    shoulder_width = np.linalg.norm(pts[12] - pts[11]) + 1e-9
    hip_width = np.linalg.norm(pts[24] - pts[23])
    features.append(hip_width / shoulder_width)

    head_y = pts[0][1]
    hip_y = (pts[23][1] + pts[24][1]) / 2
    ankle_y = (pts[27][1] + pts[28][1]) / 2
    wrist_y = (pts[15][1] + pts[16][1]) / 2
    shoulder_y = (pts[11][1] + pts[12][1]) / 2

    features.append((head_y - hip_y) / shoulder_width)
    features.append((ankle_y - hip_y) / shoulder_width)
    features.append((wrist_y - shoulder_y) / shoulder_width)

    # ── Symmetry features ──
    features.append(abs(elbow_l - elbow_r))
    features.append(abs(knee_l - knee_r))

    # ── Body center ──
    com = (pts[11] + pts[12] + pts[23] + pts[24]) / 4
    features.append(com[1] / shoulder_width)

    # ── Forward lean ──
    nose_z = pts[0][2]
    hip_z = (pts[23][2] + pts[24][2]) / 2
    features.append((nose_z - hip_z) / shoulder_width)

    # ── Spread features ──
    wrist_dist = np.linalg.norm(pts[16] - pts[15])
    ankle_dist = np.linalg.norm(pts[28] - pts[27])
    features.append(wrist_dist / shoulder_width)
    features.append(ankle_dist / shoulder_width)

    # ── NEW: Additional discriminative features ──
    
    # Torso angle (average of left/right)
    features.append((torso_vert_l + torso_vert_r) / 2)
    
    # Leg angle (average)
    features.append((upper_leg_vert_l + upper_leg_vert_r) / 2)
    
    # Arm angle (average)
    features.append((upper_arm_vert_l + upper_arm_vert_r) / 2)
    
    # Head position in z (forward/backward)
    features.append(pts[0][2] / shoulder_width)
    
    # Hip height relative to shoulders
    features.append((hip_y - shoulder_y) / shoulder_width)
    
    # Knee height relative to hips
    knee_y = (pts[25][1] + pts[26][1]) / 2
    features.append((knee_y - hip_y) / shoulder_width)
    
    # Wrist height relative to hips
    features.append((wrist_y - hip_y) / shoulder_width)
    
    # Body span (head to ankle distance)
    body_span = np.linalg.norm(pts[0] - (pts[27] + pts[28]) / 2)
    features.append(body_span / shoulder_width)
    
    # Shoulder-hip horizontal distance (lean indicator)
    shoulder_mid = (pts[11] + pts[12]) / 2
    hip_mid = (pts[23] + pts[24]) / 2
    horizontal_dist = np.linalg.norm(shoulder_mid[[0,2]] - hip_mid[[0,2]])
    features.append(horizontal_dist / shoulder_width)

    return np.array(features, dtype=np.float32)
