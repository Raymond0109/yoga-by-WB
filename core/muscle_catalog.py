"""Authoritative muscle catalog + per-asana seed levels for the calibrator.

This module is the SINGLE SOURCE OF TRUTH for *which* muscles exist and how
they are drawn. Both the calibrator frontend (via /api/asanas) and the main
analyzer read from here (the analyzer's ID_MAP already covers every canonical
id below, so expanding asanas.json to these ids is safe and even fixes the
old "traps always REST" fallback bug).

Canonical muscle ids (13):
  hamstrings, quads, glutes, calves, deltoids, triceps, biceps, forearm,
  obliques, rectus, spinal, traps, pectoral

Draw metadata:
  - limb muscles: a `segment` (BlazePose indices) + anatomical `face`
    ('front'/'back'/'outer') + `width` factor, rendered via drawBelly.
  - special muscles (pectoral/rectus/traps/spinal): drawn by bespoke geometry
    routines in the frontend, keyed by `special`.
"""
from __future__ import annotations

# --- Anatomical reference sizes (公开医学文献, PCSA 生理横截面积 cm²) ---
# Source: peer-reviewed MRI/cadaver PCSA compilations (NCBI/PMC, e.g. Ward et al.
# 2013; Lube et al. 2017; Abe et al. sprinter CSA tables). PCSA is the standard
# anatomical proxy for muscle belly *thickness / cross-section* (force capacity),
# so it drives how thick each rendered muscle bundle should look. Values below are
# representative single-muscle (or representative belly) PCSA in cm², rounded.
PCSA = {
    "glutes":     55.0,   # gluteus maximus — 人体最大肌肉
    "quads":      50.0,   # 股四头肌群(单绘侧腹)
    "calves":     42.0,   # 腓肠肌+比目鱼肌(单绘侧腹)
    "hamstrings": 38.0,   # 腘绳肌群(单绘侧腹)
    "obliques":   28.0,   # 腹斜肌(外侧腹壁)
    "traps":      28.0,   # 斜方肌
    "pectoral":   26.0,   # 胸大肌
    "spinal":     25.0,   # 竖脊肌(骶棘肌)
    "triceps":    24.0,   # 肱三头肌
    "deltoids":   16.0,   # 三角肌
    "forearm":    15.0,   # 前臂肌群
    "biceps":     12.0,   # 肱二头肌
    "rectus":      9.0,   # 腹直肌
}
_PMAX, _PMIN = max(PCSA.values()), min(PCSA.values())
# Map PCSA -> rendered belly half-width factor in [0.12, 0.26] (anatomy-driven).
# The belly half-width is a fraction of the bone/segment length, so this keeps
# gluteus maximus visibly thicker than biceps while staying within a sane
# on-screen proportion. Monotonic in PCSA -> the anatomical ordering is preserved.
def _width_from_pcsa(pcsa: float) -> float:
    t = (pcsa - _PMIN) / ((_PMAX - _PMIN) or 1.0)
    return round(0.12 + 0.14 * max(0.0, min(1.0, t)), 3)

# id -> draw metadata
CATALOG = {
    "hamstrings": dict(name_zh="腘绳肌(腿后侧)", segment=[24, 26], side="both",
                        special=None, face="back", pcsa=PCSA["hamstrings"]),
    "quads":      dict(name_zh="股四头肌", segment=[24, 26], side="both",
                        special=None, face="front", pcsa=PCSA["quads"]),
    "glutes":     dict(name_zh="臀大肌", segment=[24, 26], side="both",
                        special=None, face="back", pcsa=PCSA["glutes"]),
    "calves":     dict(name_zh="小腿肌(腓肠肌)", segment=[26, 28], side="both",
                        special=None, face="back", pcsa=PCSA["calves"]),
    "deltoids":   dict(name_zh="三角肌", segment=[12, 14], side="both",
                        special=None, face="outer", pcsa=PCSA["deltoids"]),
    "triceps":    dict(name_zh="肱三头肌", segment=[12, 14], side="both",
                        special=None, face="back", pcsa=PCSA["triceps"]),
    "biceps":     dict(name_zh="肱二头肌", segment=[12, 14], side="both",
                        special=None, face="front", pcsa=PCSA["biceps"]),
    "forearm":    dict(name_zh="前臂肌群", segment=[14, 16], side="both",
                        special=None, face="front", pcsa=PCSA["forearm"]),
    "obliques":   dict(name_zh="腹斜肌", segment=[12, 24], side="both",
                        special=None, face="outer", pcsa=PCSA["obliques"]),
    "rectus":     dict(name_zh="腹直肌", segment=None, side="both",
                        special="rectus", face="front", pcsa=PCSA["rectus"]),
    "spinal":     dict(name_zh="竖脊肌(骶棘肌)", segment=None, side="both",
                        special="spinal", face="back", pcsa=PCSA["spinal"]),
    "traps":      dict(name_zh="斜方肌", segment=None, side="both",
                        special="traps", face="back", pcsa=PCSA["traps"]),
    "pectoral":   dict(name_zh="胸大肌", segment=None, side="both",
                        special="pectoral", face="front", pcsa=PCSA["pectoral"]),
}
# Derive the anatomy-driven belly width from PCSA (single source of truth).
for _cid, _meta in CATALOG.items():
    _meta["width"] = _width_from_pcsa(_meta["pcsa"])

# Stable display order in the UI.
ORDER = ["hamstrings", "quads", "glutes", "calves", "deltoids", "triceps",
         "biceps", "forearm", "obliques", "rectus", "spinal", "traps", "pectoral"]

# Map legacy asanas.json muscle ids -> canonical id.
LEGACY_MAP = {
    "quads_stand": "quads", "quads_front": "quads", "quads": "quads",
    "hip_flexors": "quads",
    "glutes_back": "glutes", "glutes": "glutes",
    "core": "__core__",  # expands to rectus + obliques
    "obliques": "obliques", "hamstrings": "hamstrings", "deltoids": "deltoids",
    "triceps": "triceps", "spinal": "spinal", "calves": "calves",
}

# Per-asana seed levels (expert starting point; the calibrator refines these).
# Every asana lists all 13 canonical muscles so the tool always shows the full
# associated set (vs the old 2-7). Levels in [0,1].
SEED = {
    "downward_dog": dict(hamstrings=.95, deltoids=.7, triceps=.5, spinal=.5, calves=.6,
                         quads=.5, glutes=.4, obliques=.3, pectoral=.3, traps=.5,
                         biceps=.2, forearm=.2, rectus=.3),
    "tree": dict(quads=.85, glutes=.6, obliques=.4, deltoids=.4, spinal=.3, hamstrings=.2,
                 calves=.4, traps=.3, biceps=.1, forearm=.1, rectus=.4, triceps=.1, pectoral=.2),
    "triangle": dict(quads=.6, obliques=.6, deltoids=.5, hamstrings=.4, calves=.4, spinal=.3,
                      glutes=.3, rectus=.3, traps=.3, biceps=.2, forearm=.2, triceps=.2, pectoral=.2),
    "warrior1": dict(quads=.7, glutes=.7, obliques=.5, deltoids=.5, spinal=.4, hamstrings=.3,
                      calves=.4, rectus=.4, traps=.4, biceps=.2, forearm=.2, triceps=.2, pectoral=.3),
    "warrior2": dict(quads=.7, glutes=.6, deltoids=.5, obliques=.5, hamstrings=.3, calves=.4,
                      spinal=.3, rectus=.3, traps=.3, biceps=.2, forearm=.2, triceps=.2, pectoral=.2),
    "warrior3": dict(quads=.8, glutes=.7, spinal=.6, deltoids=.5, obliques=.4, hamstrings=.4,
                      calves=.5, rectus=.4, traps=.5, biceps=.2, forearm=.2, triceps=.3, pectoral=.2),
    "chair": dict(quads=.9, glutes=.7, obliques=.5, deltoids=.4, spinal=.4, hamstrings=.3,
                  calves=.4, rectus=.4, traps=.3, biceps=.1, forearm=.1, triceps=.2, pectoral=.2),
    "plank": dict(obliques=.85, triceps=.7, quads=.5, spinal=.6, deltoids=.5, hamstrings=.2,
                  calves=.4, glutes=.3, rectus=.5, traps=.5, biceps=.3, forearm=.3, pectoral=.3),
    "bridge": dict(glutes=.9, hamstrings=.7, spinal=.6, quads=.5, deltoids=.3, calves=.3,
                   obliques=.3, rectus=.3, traps=.3, triceps=.2, pectoral=.2, biceps=.1, forearm=.1),
    "cobra": dict(spinal=.8, deltoids=.6, glutes=.5, quads=.4, pectoral=.6, traps=.6, triceps=.3,
                  rectus=.5, obliques=.3, calves=.3, hamstrings=.3, biceps=.2, forearm=.2),
    "camel": dict(glutes=.7, quads=.6, spinal=.6, deltoids=.5, pectoral=.7, traps=.6, triceps=.3,
                  rectus=.5, obliques=.4, calves=.4, hamstrings=.3, biceps=.2, forearm=.2),
    "boat": dict(quads=.7, obliques=.9, deltoids=.4, hamstrings=.3, spinal=.4, glutes=.3, rectus=.6,
                 traps=.3, triceps=.2, pectoral=.3, biceps=.2, forearm=.2, calves=.4),
    "handstand": dict(deltoids=.9, triceps=.85, obliques=.7, quads=.5, calves=.6, spinal=.5,
                      glutes=.4, hamstrings=.3, traps=.7, biceps=.4, forearm=.4, rectus=.5, pectoral=.3),
    "crow": dict(deltoids=.9, triceps=.85, obliques=.8, quads=.6, glutes=.4, spinal=.5, hamstrings=.3,
                 calves=.4, traps=.7, biceps=.4, forearm=.4, rectus=.5, pectoral=.3),
    "paschimottanasana": dict(hamstrings=.9, spinal=.6, calves=.7, quads=.5, obliques=.4, rectus=.4,
                              glutes=.3, deltoids=.2, traps=.2, triceps=.1, pectoral=.2, biceps=.1, forearm=.1),
    "upavistha_konasana": dict(hamstrings=.85, quads=.55, spinal=.5, obliques=.5, rectus=.4, calves=.5,
                               glutes=.3, deltoids=.2, traps=.2, triceps=.1, pectoral=.2, biceps=.1, forearm=.1),
    "salabhasana": dict(spinal=.9, glutes=.7, hamstrings=.6, deltoids=.5, quads=.4, calves=.4,
                        obliques=.3, traps=.5, triceps=.3, pectoral=.3, rectus=.4, biceps=.2, forearm=.2),
    "dhanurasana": dict(spinal=.85, glutes=.7, quads=.6, deltoids=.5, hamstrings=.5, pectoral=.6,
                        traps=.5, rectus=.5, calves=.4, obliques=.4, triceps=.3, biceps=.2, forearm=.2),
    "makarasana": dict(spinal=.6, deltoids=.4, quads=.3, glutes=.3, rectus=.3, hamstrings=.3, calves=.3,
                       obliques=.2, traps=.3, triceps=.2, pectoral=.3, biceps=.1, forearm=.1),
    "natarajasana": dict(quads=.8, glutes=.6, obliques=.6, deltoids=.5, hamstrings=.5, spinal=.5,
                         rectus=.4, calves=.4, traps=.4, triceps=.3, pectoral=.3, biceps=.2, forearm=.2),
    "garudasana": dict(quads=.7, glutes=.6, obliques=.6, deltoids=.5, spinal=.4, hamstrings=.3,
                       calves=.4, rectus=.4, traps=.3, triceps=.2, pectoral=.2, biceps=.2, forearm=.2),
    "urdhva_dhanurasana": dict(deltoids=.85, triceps=.7, glutes=.8, quads=.6, spinal=.7, calves=.5,
                               obliques=.4, pectoral=.6, traps=.6, rectus=.5, hamstrings=.4, biceps=.3, forearm=.3),
    "pincha_mayurasana": dict(deltoids=.8, triceps=.8, obliques=.8, glutes=.5, spinal=.6, quads=.5,
                              calves=.5, hamstrings=.3, traps=.8, biceps=.4, forearm=.4, rectus=.5, pectoral=.3),
    "extended_hand_to_toe": dict(quads=.7, hamstrings=.6, calves=.6, glutes=.4, obliques=.6, deltoids=.5,
                                 spinal=.4, rectus=.4, traps=.4, triceps=.2, pectoral=.3, biceps=.2, forearm=.2),
    "gate": dict(quads=.7, obliques=.7, spinal=.5, deltoids=.4, glutes=.4, hamstrings=.3, rectus=.4,
                 calves=.3, traps=.3, triceps=.2, pectoral=.3, biceps=.1, forearm=.1),
    "low_lunge": dict(quads=.8, glutes=.6, obliques=.5, deltoids=.5, hamstrings=.4, spinal=.4,
                      rectus=.4, calves=.4, traps=.3, triceps=.2, pectoral=.3, biceps=.2, forearm=.2),
    "side_angle": dict(quads=.7, obliques=.7, glutes=.6, deltoids=.5, hamstrings=.3, spinal=.4,
                       rectus=.4, calves=.4, traps=.4, triceps=.2, pectoral=.3, biceps=.2, forearm=.2),
}


def canonical_id(legacy_id: str) -> str | None:
    """Map a legacy asanas.json muscle id to a canonical id, or None if unknown."""
    return LEGACY_MAP.get(legacy_id, legacy_id if legacy_id in CATALOG else None)


def build_muscles(asana_id: str, existing: list[dict]) -> list[dict]:
    """Build the expanded muscle list for one asana.

    Existing curated levels are preserved; SEED fills gaps. Draw metadata
    (name_zh/segment/side/face/width/special) comes from CATALOG.
    """
    levels: dict[str, float] = {}
    names: dict[str, str] = {}
    for m in existing:
        cid = canonical_id(m["id"])
        if cid is None:
            continue
        if cid == "__core__":
            lvl = float(m.get("level", 0.0))
            for tgt in ("rectus", "obliques"):
                if tgt not in levels:
                    levels[tgt] = lvl
            continue
        lvl = float(m.get("level", 0.0))
        if cid not in levels:
            levels[cid] = lvl
        if m.get("name_zh"):
            names[cid] = m["name_zh"]

    seed = SEED.get(asana_id, {})
    for cid, lvl in seed.items():
        if cid not in levels:
            levels[cid] = lvl

    out = []
    for cid in ORDER:
        if cid not in levels:
            continue
        meta = CATALOG[cid]
        out.append({
            "id": cid,
            "name_zh": names.get(cid, meta["name_zh"]),
            "segment": meta["segment"],
            "side": meta["side"],
            "special": meta["special"],
            "face": meta["face"],
            "width": meta["width"],
            "pcsa": meta["pcsa"],
            "level": round(levels[cid], 3),
        })
    return out
