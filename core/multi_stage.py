"""Multi-stage asana classifier v3: Gentle filtering.

Only filters out obviously incompatible asanas (e.g. inversions for
non-inverted poses). This prevents false negatives while still reducing
the candidate pool for clearly different pose types.
"""

from __future__ import annotations
import numpy as np


def filter_candidates(world_landmarks: list[dict], asana_ids: list[str]) -> list[str]:
    """Return subset of asana_ids that pass gentle geometric filters.

    Only excludes asanas that are CLEARLY incompatible with the observed pose.
    Returns full list if filters would eliminate all candidates.
    """
    if not world_landmarks:
        return asana_ids

    pts = np.array([[p["x"], p["y"], p["z"]] for p in world_landmarks], dtype=float)

    # Detect if pose is inverted (head below feet in y-up coords)
    head_y = pts[0][1]
    ankle_y = min(pts[27][1], pts[28][1])
    is_inverted = head_y > ankle_y + 0.15  # head significantly below feet

    # Detect if body is roughly horizontal (shoulders and hips similar height)
    shoulder_y = (pts[11][1] + pts[12][1]) / 2
    hip_y = (pts[23][1] + pts[24][1]) / 2
    is_horizontal = abs(shoulder_y - hip_y) < 0.08

    survivors = []
    inversion_ids = {"handstand", "pincha_mayurasana"}

    for aid in asana_ids:
        # Skip inversions if pose is clearly not inverted
        if aid in inversion_ids and not is_inverted:
            continue
        # Skip non-inversions if pose is clearly inverted
        if aid not in inversion_ids and is_inverted:
            continue
        survivors.append(aid)

    return survivors if survivors else asana_ids
