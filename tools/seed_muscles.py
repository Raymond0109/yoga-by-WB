"""Expand every asana's `muscles[]` in data/asanas.json using core.muscle_catalog.

Additive & idempotent:
  - keeps all non-muscle fields (rules, aliases, cautions, details, benefits...)
  - preserves previously curated muscle levels
  - fills gaps from SEED so each asana lists the full associated muscle set
  - attaches draw metadata (segment/side/face/width/special) from CATALOG
"""
from __future__ import annotations
import json
from pathlib import Path
from core.muscle_catalog import build_muscles

ROOT = Path(__file__).resolve().parent.parent
ASANA_PATH = ROOT / "data" / "asanas.json"


def main():
    data = json.loads(ASANA_PATH.read_text(encoding="utf-8"))
    changed = 0
    for a in data["asanas"]:
        new_muscles = build_muscles(a["id"], a.get("muscles", []))
        old = a.get("muscles", [])
        if old != new_muscles:
            changed += 1
        a["muscles"] = new_muscles
    ASANA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(a["muscles"]) for a in data["asanas"])
    print(f"Expanded {changed}/{len(data['asanas'])} asanas; total muscle entries now {total}.")


if __name__ == "__main__":
    main()
