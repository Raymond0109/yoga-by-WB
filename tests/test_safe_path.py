"""B8: uploaded media paths must stay under data/uploads/."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as yoga_app


def test_safe_upload_path_rejects_escape(tmp_path, monkeypatch):
    upload = tmp_path / "uploads"
    upload.mkdir()
    monkeypatch.setattr(yoga_app, "UPLOAD_DIR", str(upload))
    monkeypatch.setattr(yoga_app, "_UPLOAD_REAL", os.path.realpath(str(upload)))

    # inside is ok once the file exists
    f = upload / "a.mp4"
    f.write_bytes(b"x")
    assert yoga_app._safe_upload_path(str(f)) == os.path.realpath(str(f))

    # traversal / absolute outside
    try:
        yoga_app._safe_upload_path(str(tmp_path / "secret.txt"))
        assert False, "expected ValueError"
    except ValueError as e:
        assert "允许" in str(e) or "不在" in str(e)

    try:
        yoga_app._safe_upload_path("")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_reference_world_rejects_path_traversal():
    # asana ids with path segments must not leak filesystem content
    r = yoga_app.reference_world(asana="../../etc")
    assert r["world_landmarks"] is None
    r2 = yoga_app.reference_world(asana="tree/../../../etc/passwd")
    assert r2["world_landmarks"] is None
