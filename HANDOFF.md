# 项目交接文档 - Yoga Flow 智能瑜伽助手

> 最后更新: 2026-10-05
> 分支: `feature/ui-redesign`（最新 `ac650cb`，已推送 origin，工作树干净）

---

## 一、项目概述

**项目名称**: Yoga Flow - 智能瑜伽助手
**项目路径**: `/Users/ching-juichang/Yoga_project_v1_workbuddy`
**GitHub**: https://github.com/Raymond0109/yoga-by-WB
**主要功能**: 实时瑜伽体式识别、对比回正、肌肉解剖显示（2D + 3D）

---

## 二、当前状态（2026-10-05）

### 分支情况

| 分支 | 状态 | 说明 |
|------|------|------|
| `main` | ✅ 稳定 | a806484（v0.6.2，含 7/19 推送） |
| `feature/learned-classifier` | ✅ 已合并到main | 学习分类器、55 体式 |
| `feature/ui-redesign` | ✅ 全部完成并推送 | 新UI重构**全部完成**，最新 `ac650cb` |

### 功能完成度

| 功能模块 | 完成度 | 状态 |
|----------|--------|------|
| 体式识别引擎 | 100% | ✅ 完成 |
| 学习分类器 | 100% | ✅ 完成 (LOO ~72%) |
| 体式数据库 | 100% | ✅ 55 个体式 |
| 流瑜伽序列识别 | 100% | ✅ 完成 |
| 帧间平滑 | 100% | ✅ 完成 |
| 原版UI | 100% | ✅ 完成 |
| **新版UI** | **100%** | ✅ 全部完成（含 55 列表 + 3D avatar） |

### 新版 UI 完成清单（全部已提交）

1. **drawFrame 不渲染** — 缺 `data:image/jpeg;base64,` 前缀 → 已兼容两种 payload（`fbd7fcd`）。
2. **图片上传静默失败** — WS 竞态 → `ensureConnected()`（`fbd7fcd`）。
3. **2D 肌肉覆盖层缺失** — 从 `index.html` 整体移植（`5a0de31`）。
4. **肌肉颜色不反映真实发力** — 改为实时关节角 `stretchOf` 驱动（蓝=拉伸/红=收缩，与 3D 同源）（`5a0de31`）。
5. **竖脊肌(spinal) TDZ 渲染 bug** — `side` 声明前引用 → 移入循环（`5a0de31`）。
6. **自动识别 + 视频崩溃** — `compare()` 返回 None 时 `feedback["detected"]=det` 抛 TypeError → 断流；已兜底 + `break→continue`（`5a0de31`）。
7. **55 体式列表渲染** — `renderPoseListFromMap(ASANA_MAP)`（`dc1445e`）。
8. **3D avatar 接入新版 UI** — Three.js + OrbitControls + `static/avatar3d.js`（`4ef8dfc`）。
9. **上传调试与连接修复**（`081a399`）。
10. **🐞 死页回归修复（`ac650cb`，2026-09-30）** — `4ef8dfc` 曾把 ES `import` 放进经典 `<script>` → `SyntaxError` 杀死整个脚本块（页面全空）；且 `avatar3d.js` 顶层 `const STRETCH_RANGE/STRETCH_CFG` 与主页面全局冲突 → avatar3d 不加载。修复：3D 段独立 `<script type="module">` + `avatar3d.js` 整体 IIFE 包裹。

### 测试状态（全绿）

- `pytest` **34/34 PASS**
- `tests/e2e_ui_redesign.js`（Puppeteer）**16/16 PASS**，JS 异常 0
  - 含 5 项**架构回归断言**：经典脚本解析（drawFrame/drawMuscles 存在）、ASANA_MAP=55、列表渲染 55 项、3D avatar 加载（init3D/THREE/Avatar3D）、avatar3d 无全局冲突 pageerror
- `tests/smoke_autodetect_video.py`（真实上传视频+`__auto__`）**PASS**：frames=36/errors=0/detected=36，识别 `camel`

---

## 三、技术架构

### 核心文件

| 文件 | 说明 |
|------|------|
| `app.py` | FastAPI后端，WebSocket `/ws`；`_send_frame`/`_stream` 主循环 |
| `core/pose_compare.py` | 体式比较 `compare()` / `detect_asana()` / `best_candidate()` |
| `core/classifier_v2.py` | 学习分类器（LOO ~72%） |
| `data/asanas.json` | 体式数据库 (55个) |
| `static/index.html` | 原版UI（含 3D avatar） |
| `static/ui-redesign.html` | 新版UI：经典 `<script>`（2D/肌肉/交互）+ `<script type="module">`（3D 初始化） |
| `static/avatar3d.js` | 3D avatar 模块（**整体 IIFE 包裹**，仅暴露 `window.init3D`/`window.Avatar3D`） |

### ⚠️ 前端架构约定（防死页回归）

- `ui-redesign.html` 的**经典脚本块内禁止使用 `import`/`export`**（SyntaxError 会杀死整个块）。需要 ES 模块时用独立 `<script type="module">`。
- 任何以经典 `<script>` 加载的 JS 文件（如 `avatar3d.js`）**必须 IIFE 包裹**，避免与主页面全局同名（`STRETCH_RANGE`/`STRETCH_CFG`/`POSE_CONNECTIONS` 等）。
- importmap（unpkg CDN `three@0.160.0`）需外网；离线环境 3D 不可用（2D 不受影响）。

### API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 原版UI |
| `/static/ui-redesign.html` | GET | 新版UI |
| `/api/asanas` | GET | 55 体式列表 |
| `/api/upload` | POST | 上传图片/视频（返回 `{path, kind}`） |
| `/api/reference_world` | GET | 体式标准 world 坐标（3D ghost） |
| `/ws` | WebSocket | `{type:'start', asanaId, source, path}` / `{type:'frame', data}` → `frame`+`poses`+`feedback` |

---

## 四、待办事项（接手顺序）

### 🟡 中优先级（路线图，核心功能已全部完成）

- [ ] #11 规则深度校准（工具 `calibrator` 就绪，数据未标）
- [ ] #13 张力模型升级（`live=base×(0.4+0.6×score/100)` 启发式未标定）
- [ ] 完善偏简单的体式规则（平均 4.1 条/体式）
- [ ] 分类准确率提升（当前 ~72% LOO）

### 🟢 低优先级

- [ ] #15 报告 PDF 导出
- [ ] handstand/crow/extended_hand_to_toe 补标参考骨架（分类器不输出，需专家上传）
- [ ] 可复现性：`data/models/*.pkl` + `data/ref/` gitignored，全新 clone 需重建
- [ ] 移动端适配 / API 文档 / README 更新

---

## 五、运行指南

### 启动服务器

```bash
cd /Users/ching-juichang/Yoga_project_v1_workbuddy
source /Users/ching-juichang/.workbuddy/binaries/python/envs/default/bin/activate
pkill -f "uvicorn app:app"      # 先杀旧进程
uvicorn app:app --port 8000
```

### 运行测试

```bash
# 后端单测（无需服务器）
/Users/ching-juichang/.workbuddy/binaries/python/envs/default/bin/python -m pytest tests/ -q

# 前端 e2e（需 :8000 在跑；node 路径带 -3 后缀）
NODE_PATH=/Users/ching-juichang/.workbuddy/binaries/node/workspace/node_modules \
  /Users/ching-juichang/.workbuddy/binaries/node/versions/22.22.2-3/bin/node tests/e2e_ui_redesign.js

# 自动识别+视频 端到端（需 :8000 在跑）
/Users/ching-juichang/.workbuddy/binaries/python/envs/default/bin/python tests/smoke_autodetect_video.py
```

### 访问链接
- **原版UI**: http://localhost:8000
- **新版UI**: http://localhost:8000/static/ui-redesign.html

---

## 六、关键数据

| 指标 | 值 |
|------|-----|
| 总体式数 | 55（standing 17 / seated 10 / balancing 6 / prone 6 / inversion 5） |
| 规则总数 | 225（平均 4.1 条/体式） |
| 准确率 | 规则 52.5% / 学习分类器 ~72% (LOO) |
| 测试 | pytest 34/34 ✅ · e2e 16/16 ✅ · smoke PASS ✅ |

---

## 七、版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v0.6.4 | 2026-10-05 | 55体式列表 + 3D avatar 接入新UI + 死页回归修复（module 拆分 + avatar3d IIFE）+ e2e 架构断言 |
| v0.6.3 | 2026-07-22 | 新UI调试完成：肌肉层+姿势着色+spine TDZ+auto-detect视频崩溃修复 |
| v0.6.2 | 2026-07-21 | UI重构、外部数据集集成、序列识别 |
| v0.6.1 | 2026-07-19 | 新增12个体式、修正PDF |
| v0.6.0 | 2026-07-18 | 学习分类器、准确率提升 |
| v0.5.4 | 2026-07-17 | Bug修复 (B1-B10) |

---

## 八、环境依赖

- Python 3.13+（托管 venv `~/.workbuddy/binaries/python/envs/default/bin/python`）
- scikit-learn / mediapipe / opencv-python / fastapi / uvicorn
- Node 22（`versions/22.22.2-3/bin/node`；Puppeteer 在 `~/.workbuddy/binaries/node/workspace/node_modules`）

---

## 九、注意事项

1. **Python环境**: 必须用托管 venv，勿用系统 python（MediaPipe wheel 不兼容）。
2. **端口**: 默认 8000；重启务必先 `pkill -f "uvicorn app:app"`。
3. **摄像头**: 需经 http://localhost:8000 访问（非 file://）。
4. **模型文件**: `data/models/*.pkl` 与 `data/ref/` 均 gitignored。
5. **推送**: 当前分支 `feature/ui-redesign`；用 token-URL 推送后 `origin/*` 追踪引用**不会自动刷新**，需 `git fetch` 再看 ahead 计数（勿误判"未推送"）。
6. **后台跑 uvicorn**: 必须让 uvicorn 作为后台任务的**前台进程**（`exec uvicorn ...`）；`nohup ... &` 的子进程会在任务结束被沙箱收割。

---

## 十、接手建议

1. 核心功能（含 55 列表、3D avatar）已全部完成，下一步是**路线图项**（#11 校准 / #13 张力模型 / #15 PDF）。
2. 改前端前先读第二节「前端架构约定」，避免死页回归。
3. 改完跑三套验证（`pytest` + `e2e_ui_redesign.js` + `smoke_autodetect_video.py`）再 commit + push `feature/ui-redesign`。
