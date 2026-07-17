"""#12 — calibrator overlay must take effect in the main app.

The calibrator writes data/asanas.calibration.json (gitignored). The main app
loads it at DB load time so uncommitted calibrations affect rendering/scoring
without modifying asanas.json. `min_sep` is a threshold and must never be
overwritten by the overlay.
"""
import json
import core.pose_compare as pc


def test_apply_calibration_overlay_merges_levels_rules_ref(monkeypatch, tmp_path):
    db = {"asanas": [
        {"id": "tree",
         "muscles": [{"id": "hamstrings", "level": 0.3},
                     {"id": "quads", "level": 0.4}],
         "rules": [{"id": "r1", "target": 90, "tol": 10, "min_sep": 5}]}
    ]}
    overlay = {
        "tree": {
            "muscles": {"hamstrings": 0.9, "quads": 0.8},
            "reference_landmarks": [[0, 0, 0, 1] for _ in range(33)],
            "rules": {"r1": {"target": 120, "tol": 15, "min_sep": 99}},
        }
    }
    p = tmp_path / "asanas.calibration.json"
    p.write_text(json.dumps(overlay), encoding="utf-8")
    monkeypatch.setattr(pc, "CALIB_PATH", str(p))
    pc._apply_calibration_overlay(db)
    a = db["asanas"][0]
    assert a["muscles"][0]["level"] == 0.9
    assert a["muscles"][1]["level"] == 0.8
    assert a["reference_landmarks"] == [[0, 0, 0, 1] for _ in range(33)]
    assert a["rules"][0]["target"] == 120
    assert a["rules"][0]["tol"] == 15
    assert a["rules"][0]["min_sep"] == 5  # threshold never overwritten


def test_apply_calibration_overlay_absent_is_noop(monkeypatch):
    db = {"asanas": [{"id": "x", "muscles": [{"id": "m", "level": 0.5}]}]}
    monkeypatch.setattr(pc, "CALIB_PATH", "/nonexistent/overlay.json")
    pc._apply_calibration_overlay(db)
    assert db["asanas"][0]["muscles"][0]["level"] == 0.5


def test_load_db_applies_overlay(monkeypatch, tmp_path):
    overlay = {"tree": {"muscles": {"hamstrings": 0.77}}}
    p = tmp_path / "asanas.calibration.json"
    p.write_text(json.dumps(overlay), encoding="utf-8")
    monkeypatch.setattr(pc, "CALIB_PATH", str(p))
    pc._cache = None
    pc._list_cache = None
    try:
        db = pc.load_db()
        tree = next((a for a in db["asanas"] if a["id"] == "tree"), None)
        assert tree is not None, "fixture asana 'tree' must exist"
        h = next((m for m in tree["muscles"] if m["id"] == "hamstrings"), None)
        assert h is not None, "asana 'tree' must define a hamstrings muscle"
        assert h["level"] == 0.77
    finally:
        pc._cache = None
        pc._list_cache = None
