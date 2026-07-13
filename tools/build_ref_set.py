"""Build a calibration reference set from the Yoga_base_ref materials.

Reads the user's reference library (named pose images + extracted video
keyframes) and produces, for every asana in data/asanas.json, a folder
`data/ref/<asana_id>/` containing one `ref_NNN.json` per reference pose.
Each json is a bare list of 33 MediaPipe *world* landmarks (the format
tools/calibrate_from_images.py consumes). This keeps the repo free of large
image binaries (data/ref/ is gitignored) while staying fully reproducible.

Sources:
  * Named images in Yoga_base_ref/{drawings,解剖,photo} — mapped to asana by
    a curated (traditional/simplified-tolerant) filename table. High confidence.
  * Video keyframes in Yoga_base_ref/Video/frames/{108,12pose,8pose}_* — each
    frame is run through our own detector + detect_asana; only frames the
    classifier confidently recognises AS the target asana (score >= MIN_SCORE)
    are added, so noise/title/transition frames never pollute a reference set.

Usage:
  python tools/build_ref_set.py
  python tools/build_ref_set.py --ref-root data/ref --src /path/to/Yoga_base_ref
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.detector import PoseDetector
from core.pose_compare import detect_asana, load_db

# Curated filename-fragment -> asana id (verified manually; covers 23/27).
# Drawn / anatomy / photo folders use traditional+simplified Chinese variants.
NAMED_MAP = {
    # drawings/
    "三角式.jpg": "triangle", "下犬式-官網-01-2048x1536.jpg": "downward_dog",
    "下犬式.jpg": "downward_dog", "低弓步式.jpg": "low_lunge",
    "側角伸展式.jpeg": "side_angle", "坐姿分腿前彎.png": "upavistha_konasana",
    "平板式.jpg": "plank", "幻椅式.jpg": "chair", "戰士一式.jpg": "warrior1",
    "戰士三式.jpg": "warrior3", "戰士二式.jpg": "warrior2", "樹式.jpg": "tree",
    "橋式.jpg": "bridge", "烏鴉式.jpeg": "crow", "眼鏡蛇式.jpg": "cobra",
    "舞王式.jpg": "natarajasana", "船式.jpg": "boat", "駱駝式.jpg": "camel",
    "鱷魚式.jpg": "makarasana",
    # 解剖/
    "三角式.webp": "triangle", "三角式1.jpg": "triangle", "下犬式1.jpg": "downward_dog",
    "侧角式.jpg": "side_angle", "坐立前屈.jpg": "paschimottanasana",
    "坐角式.webp": "upavistha_konasana", "小桥式.jpg": "bridge", "幻椅式.webp": "chair",
    "弓式.jpg": "dhanurasana", "战士1式.jpg": "warrior1", "战士2式.jpg": "warrior2",
    "战士3式.jpg": "warrior3", "战士3式+扭转.jpg": "warrior3",
    "战士一式2.webp": "warrior1", "战士二式.webp": "warrior2", "树式.jpg": "tree",
    "船式1.jpg": "boat", "蝗虫式.jpg": "salabhasana", "蝗虫式1.webp": "salabhasana",
    "轮式.jpg": "urdhva_dhanurasana", "骆驼式.jpg": "camel", "鹰式.jpg": "garudasana",
}

MIN_SCORE = 75.0      # only confidently-classified video frames become refs
MAX_PER_ASANA = 14    # cap references (named + video) to limit noise


def _extract_world(frame, det: PoseDetector):
    poses = det.detect(frame)
    if not poses:
        return None
    w = poses[0].get("world_landmarks")
    if not w or len(w) != 33:
        return None
    return w


def build(src_root: str, ref_root: str):
    db = load_db()
    det = PoseDetector()
    # asana_id -> list[world_landmarks]
    refs: dict[str, list] = {a["id"]: [] for a in db["asanas"]}

    # 1) named images (high confidence)
    for sub in ("drawings", "解剖", "photo"):
        d = os.path.join(src_root, sub)
        if not os.path.isdir(d):
            continue
        for fn, aid in NAMED_MAP.items():
            fp = os.path.join(d, fn)
            if not os.path.isfile(fp):
                continue
            img = cv2.imread(fp)
            if img is None:
                continue
            w = _extract_world(img, det)
            if w:
                refs[aid].append(w)
                print(f"  + named  {aid:24s} <- {sub}/{fn}")

    # 2) video keyframes (confidence-filtered by our own classifier)
    frames_dir = os.path.join(src_root, "Video", "frames")
    if os.path.isdir(frames_dir):
        exts = (".jpg", ".jpeg", ".png", ".webp")
        files = sorted(
            f for f in os.listdir(frames_dir)
            if f.lower().endswith(exts)
        )
        for f in files:
            fp = os.path.join(frames_dir, f)
            img = cv2.imread(fp)
            if img is None:
                continue
            poses = det.detect(img)
            if not poses:
                continue
            w = poses[0].get("world_landmarks")
            p = poses[0].get("landmarks")
            if not w or len(w) != 33:
                continue
            deta = detect_asana(w, p)
            if not deta or deta["score"] < MIN_SCORE:
                continue
            aid = deta["id"]
            if len(refs.get(aid, [])) < MAX_PER_ASANA:
                refs[aid].append(w)

    # write data/ref/<id>/ref_NNN.json (bare 33-pt list each)
    if os.path.isdir(ref_root):
        shutil.rmtree(ref_root)
    total = 0
    for aid, lst in refs.items():
        if not lst:
            continue
        d = os.path.join(ref_root, aid)
        os.makedirs(d, exist_ok=True)
        for i, w in enumerate(lst):
            # world_landmarks are already a list of {x,y,z,v} dicts, the exact
            # shape core.pose_compare.eval_rule_value expects.
            with open(os.path.join(d, f"ref_{i:03d}.json"), "w", encoding="utf-8") as fh:
                json.dump(w, fh, ensure_ascii=False)
            total += 1
        print(f"[ref] {aid:24s} {len(lst):2d} poses")
    print(f"\nWrote {total} reference poses across {sum(1 for v in refs.values() if v)} asanas -> {ref_root}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="/Users/ching-juichang/Yoga_base_ref")
    ap.add_argument("--ref-root", default="data/ref")
    args = ap.parse_args()
    build(args.src, args.ref_root)


if __name__ == "__main__":
    main()
