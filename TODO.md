# 体式自动识别优化 - TODO & 计划书

> 最后更新: 2026-07-21
> 当前分支: `feature/ui-redesign`

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
- [x] 分类器训练 (RF + SVM + KNN)
- [x] 集成到detect_asana
- [x] 准确率: 52.5% → ~72%

### Phase 3: 体式数据库扩展 (v0.6.1) - 已合并到main
- [x] 新增28个体式 (总计55个)
- [x] 整合外部数据集 (107种体式元数据)
- [x] 统一分类命名 (英文标准)
- [x] 完善梵文名称映射
- [x] 优化体式规则

### Phase 4: 高级功能 - 已合并到main
- [x] 流瑜伽序列识别 (6种序列)
- [x] 帧间平滑 (PoseSmoother)
- [x] 体式转换检测
- [x] 俯卧体式区分优化

### Phase 5: UI/UX - 进行中
- [x] 体式名称显示优化
- [x] 历史记录功能
- [x] 新版UI设计
- [ ] **新版UI功能调试** (当前任务)

---

## 三、当前状态

### 分支状态

| 分支 | 状态 | 最新提交 |
|------|------|----------|
| `main` | ✅ 稳定 | a806484 |
| `feature/ui-redesign` |   开发中 | e6fb93b |

### 核心指标

| 指标 | 值 |
|------|-----|
| 体式数量 | 55 |
| 规则总数 | 225 (平均4.1条/体式) |
| 测试通过 | 31/31 ✅ |
| 准确率 | ~72% (LOO) |

### 当前问题 (需接手完成)

**新版UI功能不工作**:
- 静态页面可访问: http://localhost:8000/static/ui-redesign.html
- WebSocket连接已修复
- 摄像头/上传功能需要调试
- 需要浏览器控制台查看具体错误

---

## 四、待办事项

### 🔴 高优先级 (需立即处理)

- [ ] **调试新版UI功能**
  - 测试摄像头启动
  - 测试文件上传 (图片/视频)
  - 测试实时体式检测
  - 修复WebSocket消息处理
  - 参考: `static/index.html` 的实现

- [ ] **验证所有功能**
  - 原版UI正常工作
  - 新版UI正常工作
  - API端点响应正确

### 🟡 中优先级

- [ ] 完善新体式规则 (部分体式规则较简单)
- [ ] 集成更多外部体式
- [ ] 优化体式分类准确率
- [ ] 添加3D Avatar到新UI

### 🟢 低优先级

- [ ] 移动端适配优化
- [ ] 添加API文档
- [ ] 更新README
- [ ] 性能优化

---

## 五、技术文档

### 关键文件位置

```
Yoga_project_v1_workbuddy/
├── app.py                    # FastAPI后端
├── core/
│   ├── pose_compare.py       # 体式比较引擎
│   ├── classifier_v2.py      # 学习分类器
│   ├── features_v2.py        # 特征提取
│   ├── sequence.py           # 序列识别
│   ├── smoothing.py          # 帧间平滑
│   └── pose_names.py         # 名称映射
├── data/
│   ├── asanas.json           # 体式数据库
│   └── models/               # 训练模型
├── static/
│   ├── index.html            # 原版UI
│   └── ui-redesign.html      # 新版UI
├── tests/                    # 测试文件
├── docs/                     # 文档
└── external_data/            # 外部数据集
```

### 运行命令

```bash
# 启动服务器
~/.workbuddy/binaries/python/envs/default/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8000

# 运行测试
~/.workbuddy/binaries/python/envs/default/bin/python3 -m pytest tests/ -q

# 访问UI
# 原版: http://localhost:8000
# 新版: http://localhost:8000/static/ui-redesign.html
```

### 调试新UI

1. 打开 http://localhost:8000/static/ui-redesign.html
2. 打开浏览器控制台 (F12 → Console)
3. 查看错误信息
4. 参考原版UI代码 `static/index.html`

---

## 六、版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
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
