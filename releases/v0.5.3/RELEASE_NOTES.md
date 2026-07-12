# Release v0.5.3 — 2026-07-12

> 留痕快照。本目录是 `Yoga_project_v1_workbuddy` 在 2026-07-12 的核心源码备份，
> 用于将来反查 / 回滚。模型文件（`data/models/*.task`）和测试上传视频
>（`data/uploads/*.mp4`）未纳入（可重新下载 / 由用户重新上传），恢复时见文末。

## 1. 这个版本是什么

瑜伽体式体态分析与矫正可视化工具的 **v0.5.3 里程碑版**。在 v0.5.2 基础上
扩库并修复了体式自动识别的 argmax 平局误判。

## 2. 相较 v0.5.2 的变更（Done）

| 模块 | 文件 | 说明 |
|---|---|---|
| 标准体式库 | `data/asanas.json` | 标准库 24 → **27** 体式；新增 `gate`(门闩式)、`low_lunge`(低位弓步)、`side_angle`(侧角式)。（注：`warrior1` 战士一式原已在 24 体式库内，本次仅修正其前序误加的重复 id，非净增） |
| 对比/纠正引擎 | `core/pose_compare.py` | `compare()` 新增返回值 `total_dev`（各规则偏差绝对值之和）；`detect_asana()` 在 argmax 平局时取 **`total_dev` 最小者**（几何最贴合），彻底解决 gate↔cobra、low_lunge↔extended_hand_to_toe、side_angle↔wheel/bridge 等相似体式误识别，无需逐对加判别规则 |
| 测试 | `tests/test_asanas.py`、`tests/test_expand.py` | 新增 3 体式自评分=100% + 正确识别断言；扩充成对判别回归；计数 24→27 |
| 版本 | `VERSION` | v0.5.2 → v0.5.3 |
| 计划书 | `yoga_pose_plan.md` §11 | 记录 v0.5.3 变更与标准库规模 |
| 调研 | `docs/dataset_research.md` §5.5/§5.6 | 标记 gate/low_lunge/side_angle 已入库 |

### 修复过程中发现并修正的问题
- 早期临时把 `gate`/`low_lunge` 的 `vertical_order` 跪姿规则 `target` 写反（应为 `-1` = 膝/脚在髋下），已校正。
- 移除了误加的重复 `warrior1` id（原 id 已在 v0.3.0–v0.5.2 的 24 体式库内），避免 `detect_asana` 命中重复 id。

## 3. 已知限制 / 风险（未解决，见 yoga_pose_plan.md）

1. **肌肉张紧度是启发式，未按真实发力标定**：`live = 目标 level × 姿态匹配得分`。
   选错体式时目标肌群本身就不对，张力条无意义。
2. 标准库 27 体式，仍缺 mountain / half_moon / reverse_warrior / child / pigeon 等（见调研 §5.5 P2-中）。
3. 参考插画 / 卡通图片 MediaPipe 常检测不到人体（poses=0），需用真人照片。
4. 计划书中的 3D 解剖 avatar 窗口（Three.js）与报告导出（PDF）尚未实现。

## 4. 如何恢复 / 回滚

```bash
cd Yoga_project_v1_workbuddy
# 用备份覆盖当前源码（不会动 data/models、data/uploads、.venv）
cp -R releases/v0.5.3/core/*   core/
cp    releases/v0.5.3/static/index.html  static/
cp    releases/v0.5.3/data/asanas.json   data/
cp    releases/v0.5.3/app.py releases/v0.5.3/run.sh releases/v0.5.3/requirements.txt  .

# 首次部署需安装依赖 + 让模型自动下载
~/.workbuddy/binaries/python/envs/default/bin/pip install -r requirements.txt
# 启动
./run.sh
# 浏览器打开 http://127.0.0.1:8000
```

## 5. 文件清单（本备份）

```
releases/v0.5.3/
├── app.py
├── run.sh
├── requirements.txt
├── yoga_pose_plan.md
├── core/
│   ├── __init__.py
│   ├── detector.py
│   ├── hand_detector.py
│   ├── input_source.py
│   └── pose_compare.py
├── static/
│   └── index.html
└── data/
    └── asanas.json
```
