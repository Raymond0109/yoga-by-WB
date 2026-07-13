"""Temporal landmark smoothing.

Ported (algorithm only) from the sibling TS project
``yoga-pose-analyzer`` (``src/core/pose/LandmarkSmoother.ts``).

Two layers of stabilisation on top of raw MediaPipe output:

1. **One Euro Filter** per coordinate (x/y/z) of every joint — an adaptive
   low-pass filter that removes high-frequency jitter while staying
   responsive to real movement (fast motion -> less smoothing).
2. **Keyframe lock** — when the user holds still for a few frames the
   pose is frozen, killing score/feedback flicker; it unlocks as soon as
   meaningful movement resumes. Plus low-confidence and jump rejection
   that falls back to the last good frame.

Landmarks are plain dicts ``{"x","y","z","v"}`` (or ``"visibility"``).
The smoother is *stateful* and must be created once per video stream
(see app.py), never shared across connections.
"""
from __future__ import annotations

import math
import time
from typing import Optional

DEFAULT_CONFIG = {
    "min_cutoff": 0.8,
    "beta": 0.01,
    "d_cutoff": 1.0,
    "history_size": 5,
    "min_confidence": 0.3,
    "jump_threshold": 0.15,
    "lock_threshold": 0.008,
    "lock_frame_count": 4,
    "unlock_threshold": 0.025,
}

# core joints used for movement / confidence estimation
_CORE_JOINTS = [11, 12, 23, 24, 25, 26]
_MOVE_JOINTS = [11, 12, 13, 14, 23, 24, 25, 26]


class OneEuroFilter:
    """Adaptive low-pass filter. Casiez et al., 2012."""

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x = 0.0
        self.dx = 0.0
        self.initialized = False

    @staticmethod
    def _alpha(dt: float, cutoff: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filter(self, value: float, dt: float) -> float:
        if not self.initialized:
            self.x = value
            self.dx = 0.0
            self.initialized = True
            return value
        if dt <= 0:
            return self.x
        alpha_d = self._alpha(dt, self.d_cutoff)
        dx = (value - self.x) / dt
        self.dx = alpha_d * dx + (1.0 - alpha_d) * self.dx
        cutoff = self.min_cutoff + self.beta * abs(self.dx)
        alpha = self._alpha(dt, cutoff)
        self.x = alpha * value + (1.0 - alpha) * self.x
        return self.x

    def reset(self) -> None:
        self.initialized = False
        self.x = 0.0
        self.dx = 0.0


class _JointFilterBank:
    """One OneEuroFilter per (joint, axis)."""

    def __init__(self, min_cutoff, beta, d_cutoff):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.filters: dict[str, tuple[OneEuroFilter, OneEuroFilter, OneEuroFilter]] = {}

    def filter(self, index: int, x: float, y: float, z: float, dt: float):
        key = f"j{index}"
        f = self.filters.get(key)
        if f is None:
            f = (
                OneEuroFilter(self.min_cutoff, self.beta, self.d_cutoff),
                OneEuroFilter(self.min_cutoff, self.beta, self.d_cutoff),
                OneEuroFilter(self.min_cutoff, self.beta, self.d_cutoff),
            )
            self.filters[key] = f
        return (f[0].filter(x, dt), f[1].filter(y, dt), f[2].filter(z, dt))

    def reset(self) -> None:
        for triple in self.filters.values():
            for ff in triple:
                ff.reset()


class LandmarkSmoother:
    def __init__(self, **config):
        self.config = dict(DEFAULT_CONFIG)
        self.config.update(config)
        self.filter_bank = _JointFilterBank(
            self.config["min_cutoff"], self.config["beta"], self.config["d_cutoff"]
        )
        self.history: list[dict] = []
        self.last_good: Optional[list[dict]] = None
        self.last_ts = 0.0
        self.state = "tracking"
        self.locked: Optional[list[dict]] = None
        self.static_count = 0

    # -- public API -------------------------------------------------------
    def smooth(self, landmarks: list[dict], now: Optional[float] = None) -> list[dict]:
        if not landmarks:
            return landmarks
        now = time.monotonic() if now is None else now
        if self.last_ts > 0:
            dt = max(0.001, now - self.last_ts)
        else:
            dt = 0.033  # ~30 fps first-frame default
        self.last_ts = now

        confidence = self._confidence(landmarks)

        if self.state == "locked":
            movement = (
                self._avg_displacement(landmarks, self.history[-1]["landmarks"])
                if self.history
                else 999.0
            )
            if movement > self.config["unlock_threshold"]:
                # genuine movement -> release the lock and flow into normal
                # filtering (push the current frame first so the jump check
                # below sees it and does not reject the unlocking motion).
                self.state = "tracking"
                self.static_count = 0
                self.locked = None
                self._push(landmarks, confidence)
            else:
                return [dict(lm) for lm in self.locked]

        # tracking (or just-unlocked) path: reject low-confidence / jumps
        if confidence < self.config["min_confidence"] and self.last_good:
            self._push(landmarks, confidence)
            return [dict(lm) for lm in self.last_good]

        if self._detect_jump(landmarks) and self.last_good:
            self._push(landmarks, confidence)
            return [dict(lm) for lm in self.last_good]

        # keyframe lock acquisition (tracking only)
        locked = self._handle_lock(landmarks)
        if locked is not None:
            return [dict(lm) for lm in locked]

        # normal adaptive smoothing
        smoothed = []
        for i, lm in enumerate(landmarks):
            x, y, z = self.filter_bank.filter(i, lm["x"], lm["y"], lm["z"], dt)
            v = lm.get("v", lm.get("visibility", 1.0))
            smoothed.append({"x": x, "y": y, "z": z, "v": v})
        self.last_good = [dict(l) for l in smoothed]
        self._push(smoothed, confidence)
        return smoothed

    def reset(self) -> None:
        self.filter_bank.reset()
        self.history = []
        self.last_good = None
        self.last_ts = 0.0
        self.state = "tracking"
        self.locked = None
        self.static_count = 0

    # -- internals --------------------------------------------------------
    def _push(self, landmarks, confidence) -> None:
        self.history.append({"landmarks": landmarks, "confidence": confidence})
        while len(self.history) > self.config["history_size"]:
            self.history.pop(0)

    def _handle_lock(self, landmarks) -> Optional[list[dict]]:
        # Only manages the tracking -> locked transition. The locked ->
        # tracking release is handled in smooth() (before jump rejection).
        movement = (
            self._avg_displacement(landmarks, self.history[-1]["landmarks"])
            if self.history
            else 999.0
        )
        if movement < self.config["lock_threshold"]:
            self.static_count += 1
            if self.static_count >= self.config["lock_frame_count"]:
                self.state = "locked"
                self.locked = [dict(lm) for lm in (self.last_good or landmarks)]
                return self.locked
        else:
            self.static_count = 0
        return None

    def _confidence(self, landmarks) -> float:
        if not landmarks:
            return 0.0
        vis = [lm.get("v", lm.get("visibility", 0.5)) for lm in landmarks]
        avg_vis = sum(vis) / len(vis)
        core_ok = (
            sum(1 for i in _CORE_JOINTS if i < len(landmarks) and landmarks[i].get("v", 0) > 0.3)
            / len(_CORE_JOINTS)
        )
        continuity = 1.0
        if self.history:
            disp = self._avg_displacement(landmarks, self.history[-1]["landmarks"])
            continuity = max(0.0, 1.0 - disp * 5.0)
        return avg_vis * 0.3 + core_ok * 0.4 + continuity * 0.3

    def _avg_displacement(self, a, b) -> float:
        total = 0.0
        cnt = 0
        for i in _MOVE_JOINTS:
            if i < len(a) and i < len(b) and a[i] and b[i]:
                dx = a[i]["x"] - b[i]["x"]
                dy = a[i]["y"] - b[i]["y"]
                total += math.hypot(dx, dy)
                cnt += 1
        return total / cnt if cnt else 0.0

    def _detect_jump(self, landmarks) -> bool:
        if len(self.history) < 2:
            return False
        last = self.history[-1]["landmarks"]
        return self._avg_displacement(landmarks, last) > self.config["jump_threshold"]
