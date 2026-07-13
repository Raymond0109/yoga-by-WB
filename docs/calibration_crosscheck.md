# Cross-Calibration Report — vs `yoga-pose-analyzer` reference DB

*Generated 2026-07-11 · Item 4 of the borrowed-ideas checklist.*

## Method
`tools/calibrate_crosscheck.py` maps the sibling repo's 38-pose
`StandardPoseDB.ts` `jointAngles` (kneeL/R, hipL/R, shoulderL/R, elbowL/R in
degrees) onto **our** comparable rules and flags divergences `> 12°`.

- `joint_angle` knee/elbow rules ↔ reference knee/elbow angles.
- `bone_orientation` thigh rules ↔ reference hip angles (hip flexion).
- `bone_orientation` arm rules ↔ reference shoulder angles via the proxy
  `arm° ≈ 180 − shoulder°` (this proxy is crude — see artifacts below).

**It reports only. It does NOT edit `data/asanas.json`.**

## Raw divergences flagged (>12°)

| our_id | rule | ref_joint | ours | ref | Δ | verdict |
|---|---|---|---|---|---|---|
| dhanurasana | knee_bend | kneeL | 70 | 120 | 50 | **real** (tol=30 partly absorbs) |
| natarajasana | lifted_leg_bent | kneeR | 70 | 90 | 20 | within tol=35 → no action |
| natarajasana | arms_reach | sh | 45 | 170 | 35 | **proxy artifact** |
| garudasana | arms_forward | sh | 70 | 140 | 30 | **proxy artifact** |
| garudasana | wrap_leg_bent | kneeR | 110 | 45 | 65 | **real** (tol=30, accepts near-straight leg) |

## Interpretation
- **garudasana `wrap_leg_bent`** — Reference 45° vs ours 110° (Δ65). In Eagle
  the wrapped leg is sharply bent and hooked around the standing calf; our
  rule (target 110, tol 30 → accepts 80–140°) effectively accepts a *near-
  straight* wrapped leg. **Recommend lowering target to ~50°** (sharp bend),
  tol ~30.
- **dhanurasana `knee_bend`** — Reference 120° vs ours 70° (Δ50). Bow-pose
  knee flexion is debatable between the two conventions; our tol=30 partly
  absorbs it. **Recommend a re-check toward ~90–100°** (mildly bent shins
  reaching for the ankles), tol ~30.
- **natarajasana `lifted_leg_bent`** — Δ20 but our tol=35 covers it. **No
  change needed.**
- **natarajasana `arms_reach` / garudasana `arms_forward`** — Both are
  **false positives** of the arm `bone_orientation ↔ shoulder-angle` proxy
  (one arm reaches back/up to grab the foot; the other is wrapped in front).
  The proxy cannot represent these complex arm orientations. **Ignore** for
  calibration; revisit only if the actual on-screen correction feels wrong.

## Decision needed
Whether to apply the two *real* target adjustments (garudasana, dhanurasana)
to `data/asanas.json` is pending user sign-off. Everything else (Items 1–3,
5) is implemented, tested (24/24), and live on `:8000`.
