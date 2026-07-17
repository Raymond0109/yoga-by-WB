# TODO / 规划 — Yoga 体式分析器

> 版本基线：**v0.5.4**（2026-07-17 巡检刷新；`HEAD` 与 `origin/main` 均 = `423edb5`，无分歧、已同步）。
> 原则：**先把核心功能端到端打磨稳**，数据库（标准库标定与扩库）留到后续专项回顾再完善。
> 巡检说明：本文件于 2026-07-17 据代码实测刷新——原 v0.3.0 基线、将 3D avatar / 自动识别 / PNG 导出误标为"未完成"均已纠正。

## ✅ 已完成（核心 + 近期）
- [x] 体式检测 + 手部检测（MediaPipe Tasks API，受管 venv Py3.13）
- [x] 标准库 **27 体式**（asanas.json，schema v1）
- [x] 对比/纠正引擎（评分 + ok/warn/off + 纠正文案；`detect_asana` + `best_candidate` 低置信度回退）
- [x] **自动识别体式**（`__auto__`：后端 `app.py:127-160` + 前端 `🤖 自动识别` 勾选框 + detected 标签）——此前误标为 P1 待做，实测已完成
- [x] 2D 骨骼渲染（程序化骨杆/骨骺/脊柱/锁骨）
- [x] 2D 肌肉渲染（医学插画风，纵向纺锤形，冷→暖着色）+ **2D 分析 PNG 截图导出**（`index.html:246 toDataURL` + `:770 download`）
- [x] 3D 解剖 avatar 双视图（Three.js）：骨架整理 + 解剖纺锤肌腹 + 半透镜 + 纵向纤维 + 拉伸着色（commit `16ea827`→`423edb5`）——此前误标为"v2 计划书遗留/未做"
- [x] 评分面板稳定（build-once / update-in-place）
- [x] 启动脚本 run.sh + 服务端 /ws、/api/asanas、/api/reference_world
- [x] 独立肌肉张力标定工具 calibrator（MVP，:8001）

## 🔴 P0 — 核心收尾（需核实/补强）
- [ ] **端到端相机 / 视频实时输入验证**：前端 UI 选择项、WebSocket 帧率、未检测到人体时的友好提示（目前多用手动上传图验证）。
- [ ] **错误与边界处理**：超大图/长视频内存、模型未下载、非人体输入的明确反馈与重试。
- [x] ~~一键导出当前分析截图（PNG）~~ → 已完成（见上）。

## 🟡 P1 — 正确性 / 集成（直接缓解张力错位主诉）
- [ ] **匹配/评分算法打磨**：采集几组真人样本，统计校准 `live = level × match` 的映射，避免部分体式过严/过松。
- [x] ~~#12 calibrator overlay 接入主程序~~ → **已完成**（commit `dacc364`）：主程序 `load_db()` 启动时加载 `data/asanas.calibration.json` overlay（肌肉 `level` / `reference_landmarks` / 规则 `target`·`tol`，**绝不覆盖 `min_sep`**）；补全 `ID_MAP`/`ID_MAP3D` 的 5 个缺失 canonical id（`forearm`/`pectoral`/`quads`/`rectus`/`traps`），标定肌肉不再被 `|| []` 静默丢弃；`/api/reference_world` 优先采用标定参考骨架驱动 3D ghost。
- [ ] **#13 张力模型升级**：从 `level × match` 启发式，改为结合关节力矩/支撑关系的更可信估算（仍非 EMG）。

## 🟢 P2 — 数据库完善（推迟，后续回顾专项做）
- [ ] **3 体式补标 `data/ref`**：`handstand` / `crow` / `extended_hand_to_toe` 已在 asanas.json 有 ID，但 `data/ref/<id>/` 无参考骨架 → 这 3 体式 3D ghost 返回 null、缺对比参考。需专家上传/补标。
- [ ] **每体式肌肉 `level` 标定**：基于真人教学/解剖资料给每体式目标肌群打分，替代当前启发默认值。
- [ ] **`rules.target/tol` 真人实测校准**：用采集的真人样本微调默认目标角与容差。

## ⚪ 计划书遗留（v2 / 架构级）
- [ ] **#15 PDF 报告导出**（代码中无任何 pdf 痕迹 → 未做）。
- [ ] **录制工具**：用户自己录标准体式进库。

## 反查方式
- 版本快照：`releases/vX.Y.Z/`（含 `RELEASE_NOTES.md`，写明恢复步骤）。
- 版本标识：`VERSION`。
- 开发日志：`.workbuddy/memory/` 每日记录；长期约定见 `.workbuddy/memory/MEMORY.md`。
