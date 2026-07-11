"""Expansion test for the v0.5.0 seated/prone/balancing additions.

Two kinds of guarantees are checked (full 23-way perfect auto-classification is
NOT claimed — argmax over 33 coarse landmarks is a heuristic; precision is raised
by the calibration tool + real photos, see plan P1-5):

1. Internal self-consistency: each new asana's rules are jointly satisfiable
   (a synthetic pose scores 100 % on its own rules) -> proves no contradictory
   / impossible targets.
2. Pairwise discrimination: the collisions we explicitly engineered against
   (seated vs seated, prone vs prone, inversion vs inversion, and the
   standing poses no longer swallowing horizontal/seated ones) resolve correctly.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pose_compare import compare, detect_asana, load_db  # noqa: E402

BASE = {
    0: (0.0, 0.70, 0.0),
    11: (-0.18, 0.55, 0.0), 12: (0.18, 0.55, 0.0),
    13: (-0.18, 0.35, 0.0), 14: (0.18, 0.35, 0.0),
    15: (-0.18, 0.15, 0.0), 16: (0.18, 0.15, 0.0),
    23: (-0.10, 0.00, 0.0), 24: (0.10, 0.00, 0.0),
    25: (-0.10, -0.45, 0.0), 26: (0.10, -0.45, 0.0),
    27: (-0.10, -0.90, 0.0), 28: (0.10, -0.90, 0.0),
}


def mk(overrides: dict) -> list:
    pts = [{"x": 0.0, "y": 0.0, "z": 0.0, "v": 1.0} for _ in range(33)]
    for i, (x, y, z) in BASE.items():
        pts[i] = {"x": x, "y": y, "z": z, "v": 1.0}
    for i, (x, y, z) in overrides.items():
        pts[i] = {"x": x, "y": y, "z": z, "v": 1.0}
    return pts


# Synthetic world-landmark poses (hip-centre origin, y-up, metres).
POSES = {
    "handstand": mk({
        11: (-0.18, -0.50, 0.0), 12: (0.18, -0.50, 0.0),
        13: (-0.18, -0.75, 0.0), 14: (0.18, -0.75, 0.0),
        15: (-0.18, -1.00, 0.0), 16: (0.18, -1.00, 0.0),
        23: (-0.10, 0.00, 0.0), 24: (0.10, 0.00, 0.0),
        25: (-0.10, 0.45, 0.0), 26: (0.10, 0.45, 0.0),
        27: (-0.10, 0.90, 0.0), 28: (0.10, 0.90, 0.0),
    }),
    "tree": mk({
        11: (-0.18, 0.55, 0.0), 12: (0.18, 0.55, 0.0),
        13: (-0.18, 0.80, 0.0), 14: (0.18, 0.80, 0.0),
        15: (-0.18, 1.05, 0.0), 16: (0.18, 1.05, 0.0),
        23: (-0.10, 0.00, 0.0), 24: (0.10, 0.00, 0.0),
        25: (-0.10, -0.45, 0.0), 27: (-0.10, -0.90, 0.0),
        26: (0.10, -0.10, 0.30), 28: (0.10, 0.00, 0.30),
    }),
    "paschimottanasana": mk({
        11: (-0.30, 0.10, 0.0), 12: (0.30, 0.10, 0.0),
        23: (-0.10, 0.00, 0.0), 24: (0.10, 0.00, 0.0),
        25: (-0.10, -0.05, 0.45), 26: (0.10, -0.05, 0.45),
        27: (-0.10, -0.10, 0.90), 28: (0.10, -0.10, 0.90),
    }),
    "upavistha_konasana": mk({
        11: (-0.30, 0.15, 0.10), 12: (0.30, 0.15, 0.10),
        23: (-0.10, 0.00, 0.0), 24: (0.10, 0.00, 0.0),
        25: (-1.20, -0.10, 0.30), 26: (1.20, -0.10, 0.30),
        27: (-2.00, -0.20, 0.50), 28: (2.00, -0.20, 0.50),
    }),
    "salabhasana": mk({
        11: (-0.18, 0.00, 0.45), 12: (0.18, 0.00, 0.45),
        13: (-0.18, 0.10, 0.30), 14: (0.18, 0.10, 0.30),
        15: (-0.18, 0.20, 0.00), 16: (0.18, 0.20, 0.00),
        23: (-0.10, 0.00, 0.0), 24: (0.10, 0.00, 0.0),
        25: (-0.10, 0.10, -0.45), 26: (0.10, 0.10, -0.45),
        27: (-0.10, 0.20, -0.90), 28: (0.10, 0.20, -0.90),
    }),
    "dhanurasana": mk({
        11: (-0.18, 0.30, 0.30), 12: (0.18, 0.30, 0.30),
        23: (-0.10, 0.00, 0.0), 24: (0.10, 0.00, 0.0),
        25: (-0.10, 0.10, -0.30), 26: (0.10, 0.10, -0.30),
        27: (-0.10, 0.45, -0.05), 28: (0.10, 0.45, -0.05),
    }),
    "makarasana": mk({
        11: (-0.18, 0.02, 0.30), 12: (0.18, 0.02, 0.30),
        13: (-0.18, -0.05, 0.30), 14: (0.18, -0.05, 0.30),
        15: (-0.18, -0.05, 0.10), 16: (0.18, -0.05, 0.10),
        23: (-0.10, 0.00, 0.0), 24: (0.10, 0.00, 0.0),
        25: (-0.10, -0.40, -0.10), 26: (0.10, -0.40, -0.10),
        27: (-0.10, -0.80, -0.20), 28: (0.10, -0.80, -0.20),
    }),
    "natarajasana": mk({
        11: (-0.18, 0.30, -0.20), 12: (0.18, 0.30, -0.20),
        15: (-0.18, 0.60, -0.10), 16: (0.18, 0.20, -0.40),
        23: (-0.10, 0.00, 0.0),
        25: (-0.10, -0.45, 0.0), 27: (-0.10, -0.90, 0.0),
        24: (0.10, 0.00, 0.0),
        26: (0.10, 0.20, -0.35), 28: (0.10, 0.45, -0.05),
    }),
    "garudasana": mk({
        11: (-0.18, 0.50, 0.0), 12: (0.18, 0.50, 0.0),
        15: (-0.40, 0.45, 0.10), 16: (0.40, 0.45, 0.10),
        23: (-0.10, 0.00, 0.0),
        25: (-0.10, -0.45, 0.0), 27: (-0.10, -0.90, 0.0),
        24: (0.10, 0.00, 0.0),
        26: (0.10, -0.30, 0.30), 28: (0.10, -0.60, 0.0),
    }),
    "urdhva_dhanurasana": mk({
        11: (-0.18, -0.50, 0.0), 12: (0.18, -0.50, 0.0),
        15: (-0.18, -0.70, 0.0), 16: (0.18, -0.70, 0.0),
        23: (-0.10, 0.30, 0.0), 24: (0.10, 0.30, 0.0),
        25: (-0.10, -0.10, 0.50), 26: (0.10, -0.10, 0.50),
        27: (-0.10, -0.50, 0.20), 28: (0.10, -0.50, 0.20),
    }),
    "pincha_mayurasana": mk({
        11: (-0.18, -0.60, 0.0), 12: (0.18, -0.60, 0.0),
        13: (-0.18, -0.80, 0.0), 14: (0.18, -0.80, 0.0),
        15: (-0.30, -0.80, 0.0), 16: (0.30, -0.80, 0.0),
        23: (-0.10, 0.00, 0.0), 24: (0.10, 0.00, 0.0),
        25: (-0.10, 0.45, 0.0), 26: (0.10, 0.45, 0.0),
        27: (-0.10, 0.90, 0.0), 28: (0.10, 0.90, 0.0),
    }),
    "cobra": mk({
        11: (-0.18, 0.20, 0.20), 12: (0.18, 0.20, 0.20),
        13: (-0.18, -0.10, 0.20), 14: (0.18, -0.10, 0.20),
        15: (-0.18, -0.25, 0.30), 16: (0.18, -0.25, 0.30),
        23: (-0.10, 0.00, 0.0), 24: (0.10, 0.00, 0.0),
        25: (-0.10, -0.05, -0.45), 26: (0.10, -0.05, -0.45),
        27: (-0.10, -0.10, -0.90), 28: (0.10, -0.10, -0.90),
    }),
}


def test_db_count_and_rules():
    db = load_db()
    asanas = db["asanas"]
    assert len(asanas) == 23, f"expected 23 asanas, got {len(asanas)}"
    valid = {"joint_angle", "bone_orientation", "level", "vertical_order"}
    for a in asanas:
        for r in a["rules"]:
            assert all(0 <= i <= 32 for i in r["indices"]), a["id"]
            assert r["type"] in valid, (a["id"], r["type"])


def test_self_consistency():
    """Every (new) pose's own rules are jointly satisfiable -> score 100."""
    for aid, lm in POSES.items():
        fb = compare(lm, aid)
        assert fb is not None, f"{aid}: no compare result"
        assert fb["score"] == 100, f"{aid}: self-score {fb['score']}"


def test_pairwise_discrimination():
    # inversions / arm-balances must not be confused with each other
    assert detect_asana(POSES["handstand"])["id"] == "handstand"
    assert detect_asana(POSES["pincha_mayurasana"])["id"] == "pincha_mayurasana"
    assert detect_asana(POSES["natarajasana"])["id"] == "natarajasana"
    assert detect_asana(POSES["urdhva_dhanurasana"])["id"] == "urdhva_dhanurasana"
    # tree / handstand regression must still hold
    assert detect_asana(POSES["tree"])["id"] == "tree"
    # seated siblings must separate
    assert detect_asana(POSES["paschimottanasana"])["id"] == "paschimottanasana"
    assert detect_asana(POSES["upavistha_konasana"])["id"] == "upavistha_konasana"
    # prone siblings must separate, and not be swallowed by cobra / triangle
    assert detect_asana(POSES["salabhasana"])["id"] == "salabhasana"
    assert detect_asana(POSES["dhanurasana"])["id"] == "dhanurasana"
    assert detect_asana(POSES["makarasana"])["id"] == "makarasana"
    assert detect_asana(POSES["cobra"])["id"] == "cobra"
    # standing poses (triangle) must no longer swallow horizontal/seated poses
    assert detect_asana(POSES["salabhasana"])["id"] != "triangle"
    assert detect_asana(POSES["makarasana"])["id"] != "triangle"
    assert detect_asana(POSES["paschimottanasana"])["id"] != "triangle"


if __name__ == "__main__":
    test_db_count_and_rules()
    test_self_consistency()
    test_pairwise_discrimination()
    print("OK: 23 asanas; self-consistency + pairwise discrimination pass")
