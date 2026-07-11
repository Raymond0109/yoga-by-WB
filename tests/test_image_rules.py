"""Tests for image-space rules and the extended_hand_to_toe asana."""
import sys

sys.path.insert(0, ".")
from core.pose_compare import compare, detect_asana, load_db


def _blank(n=33):
    return [{"x": 0.0, "y": 0.0, "z": 0.0, "v": 1.0} for _ in range(n)]


def _pose():
    """Synthetic standing hand-to-toe (right leg standing, left leg lifted side)."""
    world = _blank()
    image = _blank()
    # World: lifted left leg points up, standing right leg vertical-ish.
    world[11] = {"x": 0.05, "y": -0.40, "z": 0.0, "v": 1}
    world[12] = {"x": -0.05, "y": -0.40, "z": 0.0, "v": 1}
    world[13] = {"x": 0.10, "y": -0.25, "z": 0.0, "v": 1}   # l elbow (arm down)
    world[14] = {"x": -0.10, "y": -0.25, "z": 0.0, "v": 1}  # r elbow
    world[15] = {"x": 0.15, "y": -0.05, "z": 0.0, "v": 1}   # l wrist near hip
    world[16] = {"x": -0.15, "y": -0.05, "z": 0.0, "v": 1}  # r wrist near hip
    world[23] = {"x": 0.08, "y": -0.05, "z": 0.0, "v": 1}   # l hip
    world[24] = {"x": -0.08, "y": 0.05, "z": 0.0, "v": 1}    # r hip
    world[25] = {"x": 0.35, "y": 0.30, "z": -0.1, "v": 1}    # l knee
    world[26] = {"x": -0.08, "y": 0.35, "z": 0.0, "v": 1}    # r knee
    world[27] = {"x": 0.60, "y": 0.70, "z": -0.2, "v": 1}    # l ankle
    world[28] = {"x": -0.08, "y": 0.70, "z": 0.0, "v": 1}    # r ankle

    # Image: lifted left leg straight and to the side, ankle above hip.
    image[23] = {"x": 0.39, "y": 0.48, "v": 1}
    image[24] = {"x": 0.29, "y": 0.53, "v": 1}
    image[25] = {"x": 0.60, "y": 0.41, "v": 1}
    image[26] = {"x": 0.32, "y": 0.72, "v": 1}
    image[27] = {"x": 0.87, "y": 0.32, "v": 1}
    image[28] = {"x": 0.37, "y": 0.90, "v": 1}
    image[11] = {"x": 0.38, "y": 0.26, "v": 1}
    image[12] = {"x": 0.16, "y": 0.27, "v": 1}
    image[15] = {"x": 0.39, "y": 0.46, "v": 1}
    image[16] = {"x": 0.16, "y": 0.49, "v": 1}
    return world, image


def test_image_rule_types_exist():
    db = load_db()
    types = set()
    for a in db["asanas"]:
        for r in a["rules"]:
            types.add(r["type"])
    image_types = {"image_angle", "image_distance", "image_vertical_order"}
    assert image_types <= types, f"missing image rule types: {image_types - types}"
    print("[ok] image rule types present")


def test_extended_hand_to_toe_self():
    world, image = _pose()
    fb = compare(world, "extended_hand_to_toe", image)
    assert fb["score"] == 100, f"self score = {fb['score']}"
    print(f"[ok] extended_hand_to_toe self score = {fb['score']}")


def test_detect_prefers_extended_hand_to_toe():
    world, image = _pose()
    det = detect_asana(world, image)
    assert det is not None and det["id"] == "extended_hand_to_toe", det
    print(f"[ok] detect -> {det['id']} {det['score']}%")


def test_detect_threshold_respected():
    """detect_asana honors the threshold parameter."""
    world, image = _pose()
    # With an impossibly high threshold the same pose must be rejected.
    det = detect_asana(world, image, threshold=101)
    assert det is None, f"expected None with threshold 101, got {det}"
    print("[ok] threshold parameter is respected")


if __name__ == "__main__":
    test_image_rule_types_exist()
    test_extended_hand_to_toe_self()
    test_detect_prefers_extended_hand_to_toe()
    test_detect_threshold_respected()
    print("ALL IMAGE-RULE TESTS PASSED")
