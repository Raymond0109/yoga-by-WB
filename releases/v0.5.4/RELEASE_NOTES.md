# Release v0.5.4 — 2026-07-13

> 留痕快照。本目录是 `Yoga_project_v1_workbuddy` 在 2026-07-13 的核心源码备份，
> 用于将来反查 / 回滚。模型文件（`data/models/*.task`）、测试上传视频
>（`data/uploads/*.mp4`）、参考姿态集（`data/ref/`）、视频素材（`Yoga_base_ref/`）
> 未纳入（可重建 / 由用户重新提供），恢复时见文末。

## 1. 这个版本是什么

瑜伽体式体态分析与矫正可视化工具的 **v0.5.4 里程碑版**。在 v0.5.3 基础上完成了
实时鲁棒性收尾（时序平滑 + 几何自检 + 连续评分/反馈排序）、基于 `Yoga_base_ref`
视频素材的**数据驱动校准**，以及全部 27 体式的**元数据补充**（别名/顺位要点/常见错误）。

## 2. 相较 v0.5.3 的变更（Done）

| 模块 | 文件 | 说明 |
|---|---|---|
| 连续评分 / 反馈排序 | `core/pose_compare.py` | 每条规则给连续分（非二值）；`compare()` 返回按 \|偏差\| 排序的 `items` + `total_dev` + `low_score_tip`（分数<60 给「先纠正最差项」提示）。`get_asana_list()` 透出 aliases/cautions/details。 |
| 时序平滑 | `core/landmark_smoother.py` | One Euro Filter + 关键帧锁定，抑制实时抖动。 |
| 几何自检 | `core/geometry_check.py` | 骨长/对称性合理性校验，过滤异常 landmark。 |
| 视频校准 | `tools/build_ref_set.py`、`calibrate_from_images.py`、`calibration_diff.py`、`calibration_merge.py`、`calibrate_crosscheck.py` | 从 `Yoga_base_ref` 502 关键帧 + 命名图自建 183 条参考姿态（24 体式）；**解剖安全合并**：目标角仅在与专家顺位收敛（Δ≤8°）时微调，容差只放宽，`vertical_order` 的 min_sep（阈值）不动。最终 6 处目标微调 + 31 处容差放宽。 |
| 标准体式库 | `data/asanas.json` | 27 体式全部补充 `aliases`/`cautions`/`details`；数值按解剖安全策略并入视频校准。 |
| 元数据工具 | `tools/add_metadata.py` | 幂等写入三字段，来源知乎 p/441113137 + p/28217320 + helloyogis + 领域知识。 |
| 前端 | `static/index.html` | 选中/自动识别体式时右侧展示别名·顺位要点·常见错误；低分提示条 `#fbTip`。 |
| 测试 | `tests/` | 新增 test_feedback_ordering / test_geometry_check / test_landmark_smoother / test_scoring；全 24 测试通过。 |
| 版本 / 计划书 | `VERSION`、`yoga_pose_plan.md` §11 | v0.5.3 → v0.5.4。 |

### 校准过程中的关键决策（Fail Loudly）
- **视频均值 ≠ 正确顺位**：部分视频均值（如 side_angle 前膝 90°→114.6°、warrior1 90°→106.5°）反映练习者动作偏松/世界坐标投影偏差，与解剖顺位矛盾。策略：目标角仅接受 Δ≤8° 的收敛微调，大幅偏移一律保留专家顺位。
- **min_sep 是阈值不是容差**：`vertical_order` 的 `sep >= min_sep` 才合格，调大反而**收紧**规则（曾导致 low_lunge 误判为 extended_hand_to_toe），故保持不动。
- **容差只放宽**：不会破坏既有合成判别测试，同时吸收真实变化。

## 3. 已知限制 / 风险（未解决，见 yoga_pose_plan.md）

1. **肌肉张紧度是启发式，未按真实发力逐体式标定**：`live = 目标 level × 姿态匹配得分`。
2. crow / handstand / extended_hand_to_toe 因分类器不输出这些 id，视频校准得 0 参考，待手动补标。
3. 参考插画 / 卡通图片 MediaPipe 常检测不到人体（poses=0），需用真人照片。
4. 计划书中的 3D 解剖 avatar 窗口（Three.js）与报告导出（PDF）尚未实现。

## 4. 如何恢复 / 回滚

```bash
cd Yoga_project_v1_workbuddy
cp -R releases/v0.5.4/core/*   core/
cp    releases/v0.5.4/static/index.html  static/
cp    releases/v0.5.4/data/asanas.json   data/
cp    releases/v0.5.4/app.py releases/v0.5.4/run.sh releases/v0.5.4/requirements.txt  .

~/.workbuddy/binaries/python/envs/default/bin/pip install -r requirements.txt
./run.sh
# 浏览器打开 http://127.0.0.1:8000
```

## 5. 文件清单（本备份）

```
releases/v0.5.4/
├── app.py
├── run.sh
├── requirements.txt
├── yoga_pose_plan.md
├── core/
│   ├── __init__.py
│   ├── detector.py
│   ├── geometry_check.py
│   ├── hand_detector.py
│   ├── input_source.py
│   ├── landmark_smoother.py
│   └── pose_compare.py
├── static/
│   └── index.html
└── data/
    └── asanas.json
```
