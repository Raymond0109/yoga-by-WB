# 项目交接文档 - Yoga Flow 智能瑜伽助手

> 最后更新: 2026-07-21
> 分支: `feature/ui-redesign`

---

## 一、项目概述

**项目名称**: Yoga Flow - 智能瑜伽助手
**项目路径**: `/Users/ching-juichang/Yoga_project_v1_workbuddy`
**GitHub**: https://github.com/Raymond0109/yoga-by-WB
**主要功能**: 实时瑜伽体式识别、对比回正、肌肉解剖显示

---

## 二、当前状态

### 分支情况

| 分支 | 状态 | 说明 |
|------|------|------|
| `main` | ✅ 已合并 | 稳定版本，所有功能已合并 |
| `feature/learned-classifier` | ✅ 已合并到main | 学习分类器、体式扩展 |
| `feature/ui-redesign` |   开发中 | 新UI重构，待调试 |

### 功能完成度

| 功能模块 | 完成度 | 状态 |
|----------|--------|------|
| 体式识别引擎 | 100% | ✅ 完成 |
| 学习分类器 | 100% | ✅ 完成 (准确率~72%) |
| 体式数据库 | 100% | ✅ 55个体式 |
| 流瑜伽序列识别 | 100% | ✅ 完成 |
| 帧间平滑 | 100% | ✅ 完成 |
| 原版UI | 100% | ✅ 完成 |
| **新版UI** | **90%** | ⚠️ 需要调试 |

### 当前问题

**新版UI (`feature/ui-redesign` 分支)**:
- 静态文件已可访问
- WebSocket连接已修复
- 文件上传/摄像头/WebSocket消息处理调试完成（2026-07-22）：
  - `drawFrame` 之前直接 `img.src = msg.frame`（后端发的是**裸 base64**，无 `data:` 头）→ `<img>` 永不 load → 骨架/反馈三种输入全部不渲染。已加 `data:image/jpeg;base64,` 前缀（兼容已带前缀）。
  - `uploadFile` 调 `connect()` 后立刻发 start，但 `FileReader.onload` 早于 WS 打开 → 图片上传消息被静默丢弃。已抽出 `ensureConnected()` 先 await 连接再发。
  - 验证：`tests/e2e_ui_redesign.js`（Puppeteer）5/5 通过；pytest 31/31。
- 待补：体式选择列表仅硬编码 16 个（ASANA_MAP 已加载 55 个，列表渲染未用）；3D avatar 尚未接入新版 UI。

---

## 三、技术架构

### 核心文件

| 文件 | 说明 |
|------|------|
| `app.py` | FastAPI后端，WebSocket处理 |
| `core/pose_compare.py` | 体式比较引擎 |
| `core/classifier_v2.py` | 学习分类器 |
| `core/features_v2.py` | 特征提取 (37维) |
| `core/sequence.py` | 流瑜伽序列识别 |
| `core/smoothing.py` | 帧间平滑 |
| `core/pose_names.py` | 体式名称映射 |
| `data/asanas.json` | 体式数据库 (55个) |
| `static/index.html` | 原版UI |
| `static/ui-redesign.html` | 新版UI |

### API端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 原版UI页面 |
| `/static/ui-redesign.html` | GET | 新版UI页面 |
| `/api/asanas` | GET | 获取所有体式列表 |
| `/api/upload` | POST | 上传图片/视频 |
| `/ws` | WebSocket | 实时视频流处理 |

---

## 四、待办事项

### 高优先级 (需要接手完成)

- [x] **调试新版UI功能**
  - 打开 http://localhost:8000/static/ui-redesign.html
  - 打开浏览器控制台 (F12) 查看错误
  - 测试摄像头启动、文件上传功能
  - 修复WebSocket消息处理

- [ ] **验证所有功能正常**
  - 摄像头实时检测
  - 图片上传分析
  - 视频上传分析
  - 体式识别和反馈

### 中优先级

- [ ] 完善新体式规则 (部分体式规则较简单)
- [ ] 集成剩余外部体式 (从107种中添加更多)
- [ ] 优化体式分类准确率

### 低优先级

- [ ] 添加3D Avatar显示到新UI
- [ ] 添加体式对比动画
- [ ] 移动端适配优化
- [ ] 添加API文档
- [ ] 更新README

---

## 五、运行指南

### 启动服务器

```bash
cd /Users/ching-juichang/Yoga_project_v1_workbuddy
~/.workbuddy/binaries/python/envs/default/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

### 访问链接

- **原版UI**: http://localhost:8000
- **新版UI**: http://localhost:8000/static/ui-redesign.html

### 运行测试

```bash
~/.workbuddy/binaries/python/envs/default/bin/python3 -m pytest tests/ -q
```

---

## 六、关键数据

### 体式数据库统计

| 指标 | 值 |
|------|-----|
| 总体式数 | 55 |
| 分类 | standing(17), seated(10), balancing(6), prone(6), inversion(5) |
| 平均规则数 | 4.1 |
| 有梵文名称 | 100% |

### 准确率

| 方法 | 准确率 |
|------|--------|
| 规则系统 | 52.5% |
| 学习分类器 | ~72% (LOO交叉验证) |

### 测试状态

- 31/31 测试通过 ✅

---

## 七、版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v0.6.2 | 2026-07-21 | UI重构、外部数据集集成、序列识别 |
| v0.6.1 | 2026-07-19 | 新增12个体式、修正PDF错误 |
| v0.6.0 | 2026-07-18 | 学习分类器、准确率提升 |
| v0.5.4 | 2026-07-17 | Bug修复 (B1-B10) |

---

## 八、环境依赖

- Python 3.13+ (`~/.workbuddy/binaries/python/envs/default/bin/python`)
- scikit-learn
- mediapipe
- opencv-python
- fastapi
- uvicorn

---

## 九、注意事项

1. **Python环境**: 必须使用 `~/.workbuddy/binaries/python/envs/default/bin/python`，不要使用系统python
2. **端口**: 默认端口8000，如需修改需同时更新前端WebSocket配置
3. **摄像头**: 需要通过http://localhost:8000访问（非file://协议）
4. **模型文件**: `data/models/pose_classifier_v2.pkl` 需要训练生成

---

## 十、联系方式

- **项目所有者**: Raymond0109
- **GitHub**: https://github.com/Raymond0109/yoga-by-WB

---

## 接手建议

1. **首要任务**: 调试新版UI，确保摄像头/上传功能正常
2. **调试方法**: 打开浏览器控制台查看错误信息
3. **参考代码**: 原版UI (`static/index.html`) 的WebSocket和摄像头逻辑
4. **测试环境**: 确保在 http://localhost:8000 访问（非file://）
