# Release v0.3.0 — 2026-07-11

> 留痕快照。本目录是 `Yoga_project_v1_workbuddy` 在 2026-07-11 的核心源码备份，
> 用于将来反查 / 回滚。模型文件（`data/models/*.task`）和测试上传视频
>（`data/uploads/*.mp4`）未纳入（可重新下载 / 由用户重新上传），恢复时见文末。

## 1. 这个版本是什么

瑜伽体式体态分析与矫正可视化工具的**核心功能完成版**。从计划书（v1 草案）出发，
已实现：多源输入 → MediaPipe 检测 → 标准体式对比 → 2D 骨骼/肌肉叠加 + 矫正建议。

## 2. 已实现（Done）

| 模块 | 文件 | 说明 |
|---|---|---|
| 体式检测 | `core/detector.py` | MediaPipe PoseLandmarker，33 关键点（image xy + world xyz + visibility） |
| 手部检测 | `core/hand_detector.py` | MediaPipe HandLandmarker，21 关键点；`mp.solutions` 在 0.10 已移除，手部 21 点连接硬编码 |
| 输入抽象 | `core/input_source.py` | 图像 / 视频 / 相机统一帧迭代器 |
| 标准体式库 | `data/asanas.json` | 12 体式；schema version=1；每体式含 `muscles[].level`(0–1 目标发力) 与 `rules`(关节角/骨朝向，基于 world landmark 的启发式默认目标角) |
| 对比/纠正引擎 | `core/pose_compare.py` | `compare(world_landmarks, asana_id)` → 评分 + 每条规则的 ok/warn/off + 纠正文案；肌肉 `live = level × 匹配得分` |
| 服务端 | `app.py` | FastAPI + WebSocket `/ws` 流式推送帧+姿态+手部+反馈；`GET /api/asanas` |
| 前端 | `static/index.html` | 2D 画布叠加：程序化骨骼（骨杆+骨骺+脊柱/锁骨）、医学插画风肌肉（纵向纺锤形，肌纤维平行于骨）、按 `heat()` 冷→暖着色；评分面板 build-once / update-in-place（高度稳定） |
| 启动 | `run.sh` | 用受管 venv（Python 3.13）启动 uvicorn，端口 8000 |

### 本版本相较前序的开发修复（肌肉叠加相关）
- 肌肉方向改为基于 world landmark 解算解剖学前后/内外，不再只靠 2D 躯干中心法线。
- 肌肉画成沿骨骼纵向的纺锤形，肌纤维与骨骼平行（更符合解剖）。
- 斜方肌曾因 `neck` 点计算在倒立体式里算到脸上 → 改为锚定到肩→鼻中点，并修复 `P()` 丢弃 visibility 导致新逻辑永不触发的隐藏 bug。

## 3. 已知限制 / 风险（未解决，见 TODO.md）

1. **肌肉张紧度是启发式，未按真实发力标定**：`live = 目标 level × 姿态匹配得分`。
   选错体式时目标肌群本身就不对，张力条无意义。
2. **标准库仅 12 体式**，缺倒立 / 手臂平衡 / 坐立体式等；`muscles[].level` 与 `rules.target/tol`
   为默认启发值，需真人实测校准。
3. 2D 叠加无法区分肢体正/背面的同一对肌肉（如肱二头 vs 肱三头），靠 `face` 推断，边缘体式可能不准。
4. 参考插画 / 卡通图片 MediaPipe 常检测不到人体（poses=0），需用真人照片。
5. 计划书中的 3D 解剖 avatar 窗口（Three.js）与报告导出（PDF）尚未实现。

## 4. 如何恢复 / 回滚

```bash
cd Yoga_project_v1_workbuddy
# 用备份覆盖当前源码（不会动 data/models、data/uploads、.venv）
cp -R releases/v0.3.0/core/*   core/
cp    releases/v0.3.0/static/index.html  static/
cp    releases/v0.3.0/data/asanas.json   data/
cp    releases/v0.3.0/app.py releases/v0.3.0/run.sh releases/v0.3.0/requirements.txt  .

# 首次部署需安装依赖 + 让模型自动下载
~/.workbuddy/binaries/python/envs/default/bin/pip install -r requirements.txt
# 启动
./run.sh
# 浏览器打开 http://127.0.0.1:8000
```

## 5. 文件清单（本备份）

```
releases/v0.3.0/
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
