# 项目交接文档 - Yoga Flow 智能瑜伽助手

> 最后更新: 2026-07-22
> 分支: `feature/ui-redesign`（已提交 `5a0de31` 并推送 origin）

---

## 一、项目概述

**项目名称**: Yoga Flow - 智能瑜伽助手
**项目路径**: `/Users/ching-juichang/Yoga_project_v1_workbuddy`
**GitHub**: https://github.com/Raymond0109/yoga-by-WB
**主要功能**: 实时瑜伽体式识别、对比回正、肌肉解剖显示

---

## 二、当前状态（2026-07-22）

### 分支情况

| 分支 | 状态 | 说明 |
|------|------|------|
| `main` | ✅ 稳定 | a806484（v0.6.2，含 7/19 推送） |
| `feature/learned-classifier` | ✅ 已合并到main | 学习分类器、55 体式 |
| `feature/ui-redesign` | ✅ 开发中(本地全部提交+推送) | 新UI重构**调试完成**，最新 `5a0de31` |

### 功能完成度

| 功能模块 | 完成度 | 状态 |
|----------|--------|------|
| 体式识别引擎 | 100% | ✅ 完成 |
| 学习分类器 | 100% | ✅ 完成 (LOO ~72%) |
| 体式数据库 | 100% | ✅ 55 个体式 |
| 流瑜伽序列识别 | 100% | ✅ 完成 |
| 帧间平滑 | 100% | ✅ 完成 |
| 原版UI | 100% | ✅ 完成 |
| **新版UI** | **100%** | ✅ 调试完成（见下） |

### 新版UI调试完成清单（本阶段全部解决）

1. **drawFrame 不渲染** — 后端发裸 base64，`img.src` 缺 `data:image/jpeg;base64,` 前缀 → 已加前缀兼容两种 payload。
2. **图片上传静默失败** — `FileReader.onload` 早于 WS `open` → 抽出 `ensureConnected()` 先 await 连接再发 start。
3. **2D 肌肉覆盖层缺失** — 原版 `index.html` 完整肌肉层已整体移植进 `ui-redesign.html`（MIRROR/ID_MAP/MUSCLE_MAP/drawFusiform/drawBelly/drawSpecialMuscles/drawMuscles/heatRGB）。
4. **肌肉颜色不反映真实发力** — 改为从实时 `world_landmarks` 关节角算 `stretch`（STRETCH_CFG+angleDeg+stretchOf，与 3D avatar 同源）：0=拉伸(蓝)/1=收缩(红)。已用 e2e 证明颜色与 `feedback.live` 无关、只由姿势几何驱动。
5. **🐞 躯干竖脊肌(spinal)不渲染** — `drawSpecialMuscles` 中 `stretchOf('spinal', …, side===1?0:1)` 在 `for(const side of …)` **声明之前**引用 `side` → `const` TDZ 抛 `side is not defined`。已把计算移入循环内。
6. **🐞 自动识别 + 视频崩溃**（用户主诉"使能自动识别就不运行"）— 根因：`compare()` 返回 `None`(体式不在 55 库 / 该帧 world 空) 时，`feedback["detected"]=det` 抛 `TypeError` → 视频流 `except: break` 直接断流。修复：`feedback is None` 兜底；`_stream` 的 `break→continue`；`detect_asana` 分类器块包 `try/except` 落到 `best_candidate`。

### 测试状态（全部绿）

- `pytest` **34/34 PASS**（31 原有 + 3 新增 `tests/test_auto_detect_fix.py`）
- `tests/e2e_ui_redesign.js`（Puppeteer，需服务器运行）**11/11 PASS**，JS 异常 0
- `tests/smoke_autodetect_video.py`（真实上传视频+`__auto__`，需服务器运行）**PASS**：frames=35/errors=0/frames_with_detected=35，识别为 `camel`

### 遗留缺口（下次回来要做，见第四节）

- [ ] **体式选择列表仅硬编码 16 项**；`ASANA_MAP`（55 个）已加载但列表渲染未使用。
- [ ] **3D avatar 尚未接入新版 UI**（仅原版 `index.html` 有 Three.js 双视图 + ghost + 肌肉胶囊）。
- [ ] 路线图（历史规划）：#11 规则深度校准 / #13 张力模型升级 / #15 报告 PDF 导出 / handstand·crow·extended_hand_to_toe 无参考骨架（分类器不输出，需专家上传补标）。

---

## 三、技术架构

### 核心文件

| 文件 | 说明 |
|------|------|
| `app.py` | FastAPI后端，WebSocket `/ws`；`_send_frame`/`_stream` 为检测+对比主循环 |
| `core/pose_compare.py` | 体式比较引擎 `compare()` / `detect_asana()` / `best_candidate()` |
| `core/classifier_v2.py` | 学习分类器（LOO ~72%） |
| `core/features_v2.py` | 特征提取 (37维) |
| `core/sequence.py` | 流瑜伽序列识别 |
| `core/smoothing.py` | 帧间平滑 (One Euro + keyframe lock) |
| `data/asanas.json` | 体式数据库 (55个) |
| `static/index.html` | 原版UI（含 3D avatar 参考实现） |
| `static/ui-redesign.html` | 新版UI（当前开发焦点） |

### API端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 原版UI页面 |
| `/static/ui-redesign.html` | GET | 新版UI页面 |
| `/api/asanas` | GET | 获取所有体式列表 |
| `/api/upload` | POST | 上传图片/视频（返回 `{path, kind}`） |
| `/api/reference_world` | GET | 体式标准 world 坐标（3D ghost；无参考数据返回 null） |
| `/ws` | WebSocket | `{type:'start', asanaId, source, path}` / `{type:'frame', data}` → 回 `frame`+`poses`+`feedback` |

### WebSocket 消息协议要点
- 自动识别：`asanaId:'__auto__'` + `detect_asana()` 产出 `feedback.detected`；`compare()` 返回 None 时已兜底，永不崩。
- `feedback` 字段：`detected`/`score`/`total_dev`/`items`/`muscles`/`low_score_tip`。
- 视频源：客户端先 `POST /api/upload` 拿 `path`，再 `ws.send({type:'start', source:'video', path})`；服务器 `_stream` 解码并逐帧 `_send_frame`。

---

## 四、待办事项（接手顺序）

### 🔴 高优先级（下一个就做）

- [ ] **体式列表渲染 55 项**
  - 位置：`static/ui-redesign.html` 的 `renderPoseList()`，目前硬编码 16 项。
  - 做法：`ASANA_MAP`（已加载 55 个）驱动列表；保持搜索过滤。
  - 验证：浏览器打开新版UI，列表应显示全部 55 个体式。

- [ ] **3D avatar 接入新版 UI**
  - 参考：`static/index.html` 的 Three.js 双视图（`#view3d`）、`GET /api/reference_world` 作 ghost、30 capsule 肌肉层（commit `6844e40` 系列）。
  - 注意：新版UI是单 `<script>` 全局作用域；需把 index.html 的模块化 avatar 代码改造后并入，避免命名冲突。

### 🟡 中优先级（路线图）

- [ ] #11 规则深度校准（工具 `calibrator` 已就绪，数据未标）
- [ ] #13 张力模型升级（当前 `live=base×(0.4+0.6×score/100)` 为启发式，未标定）
- [ ] 完善部分简单体式规则（平均 4.1 条/体式，部分偏简）
- [ ] 优化分类准确率（当前 ~72% LOO）

### 🟢 低优先级

- [ ] #15 报告 PDF 导出
- [ ] handstand/crow/extended_hand_to_toe 补标参考骨架（分类器不输出这 3 个，需专家上传）
- [ ] 移动端适配、API 文档、README 更新

---

## 五、运行指南

### 启动服务器

```bash
cd /Users/ching-juichang/Yoga_project_v1_workbuddy
source /Users/ching-juichang/.workbuddy/binaries/python/envs/default/bin/activate
pkill -f "uvicorn app:app"      # 先杀旧进程，避免 address already in use
uvicorn app:app --port 8000
```

### 访问链接
- **原版UI**: http://localhost:8000
- **新版UI**: http://localhost:8000/static/ui-redesign.html

### 运行测试

```bash
# 后端单测（无需服务器）
/Users/ching-juichang/.workbuddy/binaries/python/envs/default/bin/python -m pytest tests/ -q

# 前端 e2e（需先启动 :8000）
NODE_PATH=/Users/ching-juichang/.workbuddy/binaries/node/workspace/node_modules \
  /Users/ching-juichang/.workbuddy/binaries/node/versions/22.22.2/bin/node tests/e2e_ui_redesign.js

# 自动识别+视频 端到端（需先启动 :8000）
/Users/ching-juichang/.workbuddy/binaries/python/envs/default/bin/python tests/smoke_autodetect_video.py
```

---

## 六、关键数据

### 体式数据库统计

| 指标 | 值 |
|------|-----|
| 总体式数 | 55 |
| 分类 | standing(17), seated(10), balancing(6), prone(6), inversion(5) |
| 平均规则数 | 4.1 |

### 准确率

| 方法 | 准确率 |
|------|--------|
| 规则系统 | 52.5% |
| 学习分类器 | ~72% (LOO交叉验证) |

### 测试状态

- pytest **34/34** ✅
- e2e **11/11** ✅
- smoke（auto+video）**PASS** ✅

---

## 七、版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v0.6.3 | 2026-07-22 | 新UI调试完成：肌肉层+姿势驱动着色+spine TDZ修复+auto-detect视频崩溃修复；测试 34/34 |
| v0.6.2 | 2026-07-21 | UI重构、外部数据集集成、序列识别 |
| v0.6.1 | 2026-07-19 | 新增12个体式、修正PDF错误 |
| v0.6.0 | 2026-07-18 | 学习分类器、准确率提升 |
| v0.5.4 | 2026-07-17 | Bug修复 (B1-B10) |

---

## 八、环境依赖

- Python 3.13+（托管 venv `~/.workbuddy/binaries/python/envs/default/bin/python`）
- scikit-learn / mediapipe / opencv-python / fastapi / uvicorn
- Node 22（Puppeteer e2e 用，包在 `~/.workbuddy/binaries/node/workspace/node_modules`）

---

## 九、注意事项

1. **Python环境**: 必须用托管 venv，勿用系统 python（MediaPipe wheel 不兼容）。
2. **端口**: 默认 8000；重启务必先 `pkill -f "uvicorn app:app"`。
3. **摄像头**: 需经 http://localhost:8000 访问（非 file://）。
4. **模型文件**: `data/models/*.pkl` 与 `data/ref/` 均 gitignored — 全新 clone 后分类器走规则回退、3 个无参考体式无 ghost（可复现性限制）。
5. **推送**: 当前分支 `feature/ui-redesign`；本回合只推了该分支，**未动 main / feature/learned-classifier**。如需同步 main 另行决定。

---

## 十、接手建议（下次回来直接做）

1. **首要**: 体式列表渲染 55 项（改 `renderPoseList` 用 `ASANA_MAP`）。
2. **其次**: 3D avatar 接入新版 UI（抄 `index.html` 的 Three.js 实现并适配全局作用域）。
3. 调试方法：开浏览器控制台 (F12) + 终端看 `[stream frame ERROR]`/`[detect_asana ERROR]` 打印（已加 Fail-Loudly 守卫）。
4. 改完跑 `pytest` + `e2e_ui_redesign.js` + `smoke_autodetect_video.py` 三套确认无回归，再 commit + push `feature/ui-redesign`。
