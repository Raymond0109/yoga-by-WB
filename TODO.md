# 体式自动识别优化 - TODO & 计划书

> 最后更新: 2026-07-22
> 当前分支: `feature/ui-redesign`（已提交 `5a0de31` 并推送 origin）

---

## 一、项目目标

提升流瑜伽动态体式识别准确率，支持实时教学反馈，提供友好的用户界面。

---

## 二、已完成工作 ✅

### Phase 1: Bug修复 (v0.5.4) - 已合并到main
- [x] B1: 直播中切换体式无效
- [x] B2: level tol ×100 错误
- [x] B3: 3D frontDir 反向
- [x] B4: 帧乱序
- [x] B5-B10: 其他bug修复

### Phase 2: 学习分类器 (v0.6.0) - 已合并到main
- [x] 特征提取 (37维)
- [x] 分类器训练 (RF + SVM + KNN)，LOO ~72%
- [x] 集成到 detect_asana
- [x] 准确率: 52.5% → ~72%

### Phase 3: 体式数据库扩展 (v0.6.1) - 已合并到main
- [x] 新增28个体式 (总计55个)
- [x] 整合外部数据集 (107种体式元数据)
- [x] 统一分类命名 + 完善梵文名称映射

### Phase 4: 高级功能 - 已合并到main
- [x] 流瑜伽序列识别 (6种序列)
- [x] 帧间平滑 (PoseSmoother)
- [x] 体式转换检测

### Phase 5: UI/UX 重构 - ✅ 调试完成 (2026-07-22, commit `5a0de31`)
- [x] 新版UI设计
- [x] drawFrame 渲染修复（裸 base64 前缀）
- [x] 图片上传 WS 竞态修复（ensureConnected）
- [x] 2D 肌肉覆盖层移植（从 index.html）
- [x] 肌肉颜色改为姿势驱动的实时 stretch（蓝=拉伸/红=收缩）
- [x] 🐞 躯干竖脊肌(spinal) TDZ 渲染 bug 修复
- [x] 🐞 自动识别 + 视频崩溃修复（feedback is None 兜底 + _stream break→continue）
- [x] 测试：pytest 34/34 / e2e 11/11 / smoke(auto+video) PASS

---

## 三、当前状态

### 分支状态

| 分支 | 状态 | 最新提交 |
|------|------|----------|
| `main` | ✅ 稳定 | a806484 (v0.6.2) |
| `feature/ui-redesign` | ✅ 开发中(已推送) | 5a0de31 |

### 核心指标

| 指标 | 值 |
|------|-----|
| 体式数量 | 55 |
| 规则总数 | 225 (平均4.1条/体式) |
| 测试通过 | pytest 34/34 ✅ / e2e 11/11 ✅ / smoke PASS ✅ |
| 准确率 | ~72% (LOO) |

### 当前遗留（需接手完成，按优先级见第四节）

1. **体式列表仅渲染 16 项**（硬编码）；`ASANA_MAP` 已加载 55 个但列表未用。
2. **3D avatar 未接入新版 UI**（仅原版 index.html 有）。
3. 路线图（历史规划）：#11 规则深度校准 / #13 张力模型升级 / #15 报告 PDF 导出 / handstand·crow·extended_hand_to_toe 无参考骨架。

---

## 四、待办事项

### 🔴 高优先级 (下一个就做)

- [ ] **体式列表渲染 55 项**
  - 文件：`static/ui-redesign.html` 的 `renderPoseList()`
  - 做法：用已加载的 `ASANA_MAP`（55）驱动列表，保留 `poseSearch` 过滤
  - 验证：浏览器打开新版UI，列表显示全部 55 体式

- [ ] **3D avatar 接入新版 UI**
  - 参考：`static/index.html` 的 Three.js 双视图（`#view3d`）、`GET /api/reference_world` ghost、30 capsule 肌肉层
  - 注意：新版UI为单 `<script>` 全局作用域，需改造 index.html 模块化 avatar 代码避免命名冲突

### 🟡 中优先级（路线图）

- [ ] #11 规则深度校准（工具 `calibrator` 就绪，数据未标）
- [ ] #13 张力模型升级（当前 `live=base×(0.4+0.6×score/100)` 启发式未标定）
- [ ] 完善偏简单的体式规则
- [ ] 优化分类准确率 (~72% LOO)

### 🟢 低优先级

- [ ] #15 报告 PDF 导出
- [ ] handstand/crow/extended_hand_to_toe 补标参考骨架（分类器不输出，需专家上传）
- [ ] 移动端适配
- [ ] API 文档 / README 更新

---

## 五、技术文档

### 关键文件位置

```
Yoga_project_v1_workbuddy/
├── app.py                    # FastAPI后端 (_send_frame/_stream 主循环)
├── core/
│   ├── pose_compare.py       # 体式比较引擎 compare/detect_asana/best_candidate
│   ├── classifier_v2.py      # 学习分类器
│   ├── features_v2.py        # 特征提取
│   ├── sequence.py           # 序列识别
│   ├── smoothing.py          # 帧间平滑
│   └── pose_names.py         # 名称映射
├── data/
│   ├── asanas.json           # 体式数据库(55)
│   ├── models/               # 训练模型(gitignored)
│   └── ref/                  # 视频校准参考骨架(gitignored)
├── static/
│   ├── index.html            # 原版UI(含3D avatar参考)
│   └── ui-redesign.html      # 新版UI(当前焦点)
├── tests/
│   ├── e2e_ui_redesign.js    # Puppeteer e2e(需服务器)
│   ├── smoke_autodetect_video.py # 真实上传视频+__auto__(需服务器)
│   └── test_auto_detect_fix.py   # 自动识别崩溃回归(无需服务器)
└── data/uploads/             # 上传文件(gitignored)
```

### 运行命令

```bash
# 启动服务器（先杀旧进程）
source /Users/ching-juichang/.workbuddy/binaries/python/envs/default/bin/activate
pkill -f "uvicorn app:app"; uvicorn app:app --port 8000

# 后端单测
/Users/ching-juichang/.workbuddy/binaries/python/envs/default/bin/python -m pytest tests/ -q

# 前端 e2e（需 :8000 在跑）
NODE_PATH=/Users/ching-juichang/.workbuddy/binaries/node/workspace/node_modules \
  /Users/ching-juichang/.workbuddy/binaries/node/versions/22.22.2/bin/node tests/e2e_ui_redesign.js

# 自动识别+视频 端到端（需 :8000 在跑）
/Users/ching-juichang/.workbuddy/binaries/python/envs/default/bin/python tests/smoke_autodetect_video.py

# 访问: 原版 http://localhost:8000 | 新版 http://localhost:8000/static/ui-redesign.html
```

---

## 六、版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.6.3 | 2026-07-22 | 新UI调试完成(肌肉层/姿势着色/spine TDZ/auto-detect视频崩溃)；测试34/34 |
| v0.6.2 | 2026-07-21 | UI重构、外部数据集、序列识别 |
| v0.6.1 | 2026-07-19 | 新增12体式、修正PDF |
| v0.6.0 | 2026-07-18 | 学习分类器、准确率提升 |
| v0.5.4 | 2026-07-17 | Bug修复 |

---

## 七、参考资源

- `/Users/ching-juichang/Yoga_base_ref/PDF/` - 瑜伽资料 (28份)
- `/Users/ching-juichang/Yoga_base_ref/解剖/` - 解剖图片 (48+张)
- `/Users/ching-juichang/Yoga_base/流瑜伽2.mp4` - 测试视频
- `external_data/pose_meta.json` - 107种体式元数据
