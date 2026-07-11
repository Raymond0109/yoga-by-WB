"""Auto-calibrate the asana reference DB from reference images / landmarks.

Plan §5.2 ("录制工具：从标准视频/照片提取 landmark 自动生成参考"). This is the
bridge between *public yoga datasets* (e.g. Yoga-82) or your own coach photos
and `data/asanas.json`:

  1. Collect a few "good" reference photos per asana under
     `data/ref/<asana_id>/`  (jpg/png),  OR drop ready-made world-landmark
     arrays as `data/ref/<asana_id>/landmarks.json` / `*.json`.
  2. For each reference we run MediaPipe (image mode) or read the landmarks,
     then evaluate every alignment rule's raw value via the SAME geometry
     math as `core.pose_compare.eval_rule_value`.
  3. We aggregate mean ± std across references and SUGGEST new
     `target`/`tol`/`min_sep` (human must review before merging — the engine
     is viewpoint-invariant but single-view depth is noisy).

Usage:
  python tools/calibrate_from_images.py                # all asanas w/ refs
  python tools/calibrate_from_images.py --asana-id handstand
  python tools/calibrate_from_images.py --ref-dir data/ref --out data/asanas.suggested.json

Outputs a `data/asanas.suggested.json` patch (original entries kept; only
rules that had references get updated target/tol) plus a console summary.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pose_compare import load_db, eval_rule_value

IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
# how many std-devs the tolerance should cover; clamped to a sensible floor
K = 2.0
MIN_TOL_DEG = 5.0
MIN_TOL_CM = 0.03
MIN_SEP_CM = 15.0


def _load_ref_landmarks(ref_dir: str):
    """Yield world-landmark lists for one asana ref dir (images or json)."""
    # 1) explicit landmark json files (most reproducible / testable)
    for jf in sorted(glob.glob(os.path.join(ref_dir, "*.json"))):
        with open(jf, "r", encoding="utf-8") as f:
            data = json.load(f)
        # accept either a bare list of 33 pts, or {"world_landmarks": [...]}
        if isinstance(data, list):
            yield data
        elif isinstance(data, dict) and "world_landmarks" in data:
            yield data["world_landmarks"]

    # 2) image files -> MediaPipe PoseLandmarker
    imgs = []
    for ext in IMG_EXTS:
        imgs += glob.glob(os.path.join(ref_dir, f"*{ext}"))
        imgs += glob.glob(os.path.join(ref_dir, f"*{ext.upper()}"))
    if imgs:
        try:
            from core.detector import PoseDetector
        except Exception as exc:  # pragma: no cover
            print(f"  ! MediaPipe unavailable, skipping images in {ref_dir}: {exc}")
            return
        det = PoseDetector()
        import cv2
        for im in sorted(imgs):
            frame = cv2.imread(im)
            if frame is None:
                continue
            poses = det.detect(frame)
            for p in poses:
                wl = p.get("world_landmarks")
                if wl:
                    yield wl


def _suggest(rule: dict, values: list[float]) -> dict:
    mean = statistics.mean(values)
    std = statistics.pstdev(values) if len(values) > 1 else 0.0
    t = rule["type"]
    out = dict(rule)
    if t == "vertical_order":
        out["target"] = 1 if mean > 0 else -1
        out["min_sep"] = round(max(abs(mean) * 0.6, MIN_SEP_CM), 1)
    elif t == "level":
        out["target"] = 0
        out["tol"] = round(max(std * K, MIN_TOL_CM), 3)
    else:  # joint_angle / bone_orientation (degrees)
        out["target"] = round(mean, 1)
        floor = MIN_TOL_DEG if t != "level" else MIN_TOL_CM
        out["tol"] = round(max(std * K, floor), 1)
    return out, mean, std


def calibrate(ref_root: str, asana_id: str | None, out_path: str):
    db = load_db()
    suggested = json.loads(json.dumps(db))  # deep copy
    summary = []
    for a in db["asanas"]:
        aid = a["id"]
        if asana_id and aid != asana_id:
            continue
        ref_dir = os.path.join(ref_root, aid)
        if not os.path.isdir(ref_dir):
            continue
        refs = list(_load_ref_landmarks(ref_dir))
        if not refs:
            continue
        print(f"\n[{aid}] {len(refs)} reference pose(s)")
        for i, r in enumerate(a["rules"]):
            vals = [eval_rule_value(wl, r) for wl in refs]
            vals = [v for v in vals if v is not None]
            if not vals:
                continue
            new_rule, mean, std = _suggest(r, vals)
            a_rules = suggested["asanas"][db["asanas"].index(a)]["rules"]
            a_rules[i] = new_rule
            line = (f"  · {r['id']:<22} mean={mean:7.1f}  std={std:5.1f}"
                    f"  -> target={new_rule.get('target')} tol={new_rule.get('tol', new_rule.get('min_sep'))}")
            print(line)
            summary.append((aid, r["id"], mean, std, new_rule.get("target"),
                            new_rule.get("tol", new_rule.get("min_sep"))))
    if not summary:
        print("No reference dirs found. Create data/ref/<asana_id>/ with images or landmarks.json")
        return
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(suggested, f, ensure_ascii=False, indent=2)
    print(f"\nWrote suggested DB -> {out_path}")
    print("Review the changes, then merge into data/asanas.json (this tool does NOT auto-overwrite).")


def main():
    ap = argparse.ArgumentParser(description="Calibrate asana DB from reference images/landmarks")
    ap.add_argument("--ref-dir", default="data/ref", help="root of reference folders")
    ap.add_argument("--out", default="data/asanas.suggested.json", help="suggested DB output")
    ap.add_argument("--asana-id", default=None, help="calibrate only this asana")
    args = ap.parse_args()
    calibrate(args.ref_dir, args.asana_id, args.out)


if __name__ == "__main__":
    main()
