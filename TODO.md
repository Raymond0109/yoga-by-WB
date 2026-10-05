# 体式自动识别优化 - TODO & 计划书

> 最后更新: 2026-10-05
> 当前分支: `feature/ui-redesign`（最新 `ac650cb`，已推送 origin）

---

## 一、项目目标

提升流瑜伽动态体式识别准确率，支持实时教学反馈，提供友好的用户界面。

---

## 二、已完成工作 ✅

### Phase 1: Bug修复 (v0.5.4) - 已合并到main
- [x] B1-B10 各类 bug 修复（直播切换体式、level tol ×100、3D frontDir 反向、帧乱序等）

### Phase 2: 学习分类器 (v0.6.0) - 已合并到main
- [x] 特征提取 (37维) + 分类器训练 (RF + SVM + KNN)，LOO ~72%
- [x] 集成到 detect_asana（准确率 52.5% → ~72%）

### Phase 3: 体式数据库扩展 (v0.6.1) - 已合并到main
- [x] 新增28个体式 (总计55个) + 整合外部数据集 (107种元数据)
- [x] 统一分类命名 + 梵文名称映射

### Phase 4: 高级功能 - 已合并到main
- [x] 流瑜伽序列识别 (6种序列) + 帧间平滑 (PoseSmoother) + 体式转换检测

### Phase 5: UI/UX 重构 - ✅ 全部完成 (v0.6.3 + v0.6.4)
- [x] 新版UI设计 + drawFrame 渲染修复 + 图片上传 WS 竞态修复（`fbd7fcd`）
- [x] 2D 肌肉覆盖层移植 + 姿色驱动着色 + spinal TDZ 修复 + auto-detect 视频崩溃修复（`5a0de31`）
- [x] **55 体式列表渲染**（`dc1445e`）
- [x] **3D avatar 接入新版 UI**（`4ef8dfc`）
- [x] 上传调试与连接修复（`081a399`）
- [x] **死页回归修复**：ES import 移入 `<script type="module">` + `avatar3d.js` IIFE 包裹（`ac650cb`）
- [x] e2e 增加 5 项架构回归断言（防死页复发）
- [x] 测试：pytest 34/34 · e2e 16/16（JS 异常 0）· smoke(auto+video) PASS

---

## 三、当前状态

| 分支 | 状态 | 最新提交 |
|------|------|----------|
| `main` | ✅ 稳定 | a806484 (v0.6.2) |
| `feature/ui-redesign` | ✅ 全部完成并推送 | ac650cb |

| 指标 | 值 |
|------|-----|
| 体式数量 | 55（standing 17 / seated 10 / balancing 6 / prone 6 / inversion 5） |
| 规则总数 | 225 (平均4.1条/体式) |
| 测试通过 | pytest 34/34 ✅ / e2e 16/16 ✅ / smoke PASS ✅ |
| 准确率 | 规则 52.5% / 学习分类器 ~72% (LOO) |

---

## 四、待办事项（核心功能已完成，以下为路线图）

### 🟡 中优先级

- [ ] **#11 规则深度校准**（工具 `calibrator` 就绪，数据未标）
- [ ] **#13 张力模型升级**（`live=base×(0.4+0.6×score/100)` 启发式未标定）
- [ ] 完善偏简单的体式规则
- [ ] 分类准确率提升 (~72% LOO)

### 🟢 低优先级

- [ ] #15 报告 PDF 导出
- [ ] handstand/crow/extended_hand_to_toe 补标参考骨架（分类器不输出，需专家上传）
- [ ] 可复现性：`data/models/*.pkl` + `data/ref/` gitignored
- [ ] 移动端适配 / API 文档 / README 更新

---

## 五、技术文档

### 关键文件

```
Yoga_project_v1_workbuddy/
├── app.py                    # FastAPI后端 (_send_frame/_stream)
├── core/pose_compare.py      # compare/detect_asana/best_candidate
├── data/asanas.json          # 体式数据库(55)
├── static/
│   ├── index.html            # 原版UI(含3D avatar)
│   ├── ui-redesign.html      # 新版UI(经典script + script type=module)
│   └── avatar3d.js           # 3D avatar(IIFE 包裹,暴露 window.init3D/Avatar3D)
└── tests/
    ├── e2e_ui_redesign.js    # Puppeteer e2e 16项(含架构回归断言,需:8000)
    ├── smoke_autodetect_video.py  # 上传视频+__auto__ 端到端(需:8000)
    └── test_auto_detect_fix.py    # 自动识别崩溃回归(无需服务器)
```

### 前端架构约定（防死页回归，必读）

- 经典 `<script>` 块内**禁止 `import`/`export`**（SyntaxError 杀死整块）；ES 模块用独立 `<script type="module">`。
- 经典方式加载的 JS 文件**必须 IIFE 包裹**，防与主页面全局同名（STRETCH_RANGE/STRETCH_CFG 等）。

### 运行命令

```bash
source /Users/ching-juichang/.workbuddy/binaries/python/envs/default/bin/activate
pkill -f "uvicorn app:app"; uvicorn app:app --port 8000

/Users/ching-juichang/.workbuddy/binaries/python/envs/default/bin/python -m pytest tests/ -q

NODE_PATH=/Users/ching-juichang/.workbuddy/binaries/node/workspace/node_modules \
  /Users/ching-juichang/.workbuddy/binaries/node/versions/22.22.2-3/bin/node tests/e2e_ui_redesign.js

/Users/ching-juichang/.workbuddy/binaries/python/envs/default/bin/python tests/smoke_autodetect_video.py
```

---

## 六、版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.6.4 | 2026-10-05 | 55体式列表 + 3D avatar 接入 + 死页回归修复 + e2e 架构断言 |
| v0.6.3 | 2026-07-22 | 新UI调试完成(肌肉层/姿势着色/spine TDZ/auto-detect崩溃) |
| v0.6.2 | 2026-07-21 | UI重构、外部数据集、序列识别 |
| v0.6.1 | 2026-07-19 | 新增12体式、修正PDF |
| v0.6.0 | 2026-07-18 | 学习分类器 |
| v0.5.4 | 2026-07-17 | Bug修复 |

---

## 七、参考资源

- `/Users/ching-juichang/Yoga_base_ref/PDF/` - 瑜伽资料 (28份)
- `/Users/ching-juichang/Yoga_base_ref/解剖/` - 解剖图片 (48+张)
- `/Users/ching-juichang/Yoga_base/流瑜伽2.mp4` - 测试视频
- `external_data/pose_meta.json` - 107种体式元数据
