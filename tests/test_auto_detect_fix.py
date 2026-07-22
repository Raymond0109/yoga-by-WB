"""Regression tests for the auto-detect + video crash that the user hit
("upload video shows画面, but enabling auto-detect stops it").

Root cause: in app._send_frame, when asana_id == "__auto__" and
detect_asana() returns a truthy candidate, feedback = compare(...) could be
None (asana missing from the comparison DB, or an empty world_landmarks
frame for that frame). The old code then did `feedback["detected"] = det`
which raised `TypeError: 'NoneType' object does not support item assignment`,
and the video stream's `except: break` killed the whole stream.

These tests pin the fixed behaviour: a None compare result must NEVER raise
and must surface the detected asana so the view stays alive.
"""
import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock

import numpy as np

sys.path.insert(0, "/Users/ching-juichang/Yoga_project_v1_workbuddy")
import app as app_module

_DUMMY_FRAME = np.zeros((10, 10, 3), dtype=np.uint8)  # real frame the server always passes


def _make_pose():
    lm = [{"x": 0.5, "y": 0.5, "z": 0.0, "v": 1.0} for _ in range(33)]
    wl = [{"x": 0.0, "y": 0.0, "z": 0.0, "v": 1.0} for _ in range(33)]
    return {"landmarks": lm, "world_landmarks": wl}


def _patch(detect_asana_ret, compare_ret, best_ret=None):
    app_module.detector = MagicMock()
    app_module.detector.detect.return_value = [_make_pose()]
    app_module.hand_detector = MagicMock()
    app_module.hand_detector.detect.return_value = []
    app_module.detect_asana = lambda world, image: detect_asana_ret
    app_module.compare = lambda world, aid, image: compare_ret
    app_module.best_candidate = lambda world, image: best_ret
    ws = AsyncMock()
    return ws


def _send(asana_id, detect_asana_ret, compare_ret, best_ret=None):
    ws = _patch(detect_asana_ret, compare_ret, best_ret)
    asyncio.run(
        app_module._send_frame(ws, _DUMMY_FRAME, asana_id, MagicMock(), MagicMock())
    )
    for call in ws.send_json.call_args_list:
        msg = call.args[0]
        if isinstance(msg, dict) and msg.get("type") == "frame":
            return msg
    raise AssertionError("no frame message was sent")


def test_autodetect_compare_none_does_not_crash():
    """The exact original crash: det truthy but compare() returns None."""
    msg = _send(
        "__auto__",
        detect_asana_ret={"id": "tree", "score": 0.9},
        compare_ret=None,
    )
    fb = msg["feedback"]
    assert fb is not None, "feedback must be a dict, never None"
    assert fb.get("detected", {}).get("id") == "tree"
    assert fb.get("asana_id") == "tree"


def test_autodetect_no_confidence_falls_back_to_best_candidate():
    """detect_asana returns None -> best_candidate guess, still no crash."""
    msg = _send(
        "__auto__",
        detect_asana_ret=None,
        compare_ret=None,
        best_ret={"id": "warrior", "score": 0.5, "name_zh": "战士", "name_en": "Warrior"},
    )
    fb = msg["feedback"]
    assert fb is not None
    det = fb.get("detected", {})
    assert det.get("id") == "warrior"
    assert det.get("low_confidence") is True


def test_autodetect_socket_always_sends_a_frame():
    """No matter the detection outcome, a frame must be emitted (keeps the
    video stream alive instead of breaking it)."""
    for det, cmp in [
        ({"id": "tree", "score": 0.9}, {"asana_id": "tree", "score": 80, "items": []}),
        (None, None),
        ({"id": "cobra", "score": 0.7}, None),
    ]:
        msg = _send("__auto__", detect_asana_ret=det, compare_ret=cmp)
        assert msg["type"] == "frame"
