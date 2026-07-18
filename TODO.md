# 体式自动识别优化 - TODO & 计划书

> 最后更新: 2026-07-19

## 一、项目目标

提升流瑜伽动态体式识别准确率，支持实时教学反馈。

---

## 二、已完成工作 ✅

### Phase 1: Bug修复 (v0.5.4)
- [x] B1: 直播中切换体式无效 → `pushLiveAsanaConfig()`
- [x] B2: level tol ×100 错误 → 移除自动缩放
- [x] B3: 3D frontDir 反向 → 修正向量方向
- [x] B4: 帧乱序 → 添加 frameSeq 单调计数器
- [x] B5: vertical_order 显示° → 检查单位
- [x] B6: vertical_order 非连续评分 → 添加连续评分
- [x] B7: 无feedback不清空面板 → 添加清空逻辑
- [x] B8: path traversal → 添加安全路径检查
- [x] B9: ghost竞态 → 添加请求token
- [x] B10: quads/hamstrings同向 → 修正方向

### Phase 2: 学习分类器 (v0.6.0)
- [x] 特征提取模块 (`core/features.py`, `core/features_v2.py`)
  - 28维 → 37维特征
  - 关节角度、骨骼方向、相对位置、对称性
- [x] 分类器训练 (`core/classifier.py`, `core/classifier_v2.py`)
  - 集成模型: KNN + SVM + RF
  - 特征选择: SelectKBest(k=30)
- [x] 集成到 `detect_asana()`
  - 置信度阈值: 0.5
  - Top-5 候选 + 规则比较
- [x] 准确率提升
  - 规则系统: 52.5%
  - 学习分类器: ~72% (LOO交叉验证)

### Phase 3: 体式数据库扩展 (v0.6.1)
- [x] 研究资料分析
  - 28份 PDF 资料
  - 48+29张解剖图片
  - 流瑜伽视频分析
- [x] 新增8个体式
  - upward_facing_dog (上犬式)
  - half_moon (半月式)
  - pyramid (加强侧伸展)
  - three_legged_dog (单腿下犬式)
  - pigeon (鸽子式)
  - reverse_warrior (反战式)
  - chaturanga (四柱支撑)
  - half_forward_fold (半前屈)
- [x] 体式正位修正
  - 修正PDF中的错误描述
  - 更新规则参数

---

## 三、当前状态

| 指标 | 值 |
|------|-----|
| 体式数量 | 35 |
| LOO准确率 | ~72% |
| 测试通过 | 31/31 |
| 分支 | `feature/learned-classifier` |

### 流瑜伽动态测试结果 (2026-07-19)
- 视频时长: 156.4秒
- 分析帧数: 155帧
- 识别体式: 13种

**发现的问题**:
1. 眼镜蛇式过多 (31.6%) - 俯卧体式混淆
2. 蝗虫式过多 (19.4%) - 俯卧体式混淆
3. 缺少上犬式、半月式等识别
4. 体式转换不稳定

---

## 四、待办事项 ⬜

### 高优先级
- [ ] **合并分支到 main**
- [ ] **优化俯卧体式区分**
  - 眼镜蛇式 vs 蝗虫式 vs 鳄鱼式
  - 添加手臂位置、胸部抬高规则
- [ ] **添加帧间平滑**
  - 滑动窗口平滑
  - 体式转换检测
- [ ] **测试流瑜伽动态匹配** ✅ 已完成初步测试

### 中优先级
- [ ] **新增12个体式** (中优先级)
  - 鱼式 (Fish)
  - 肩倒立 (Shoulder Stand)
  - 头倒立 (Headstand)
  - 犁式 (Plow)
  - 扭转三角式 (Revolved Triangle)
  - 扭转侧角式 (Revolved Side Angle)
  - 新月式 (Crescent Lunge)
  - 战士三式变体
  - 树式变体
  - 坐角式 (Wide-Angle)
  - 束角式 (Bound Angle)
  - 神猴式 (Splits)

- [ ] **优化现有体式规则**
  - 基于解剖资料调整target/tol
  - 添加缺失的关键规则
  - 更新肌肉发力数据

### 低优先级
- [ ] **实现流瑜伽序列识别**
  - 检测连续动作模式
  - 识别拜日式A/B
  - 提供序列级反馈

- [ ] **UI/UX优化**
  - 体式名称显示
  - 实时反馈动画
  - 历史记录

---

## 五、技术债务

- [ ] 清理备份文件 (`data/asanas.json.bak_*`)
- [ ] 清理临时测试脚本 (`tests/_*.py`)
- [ ] 更新README文档
- [ ] 添加API文档

---

## 六、关键文件

| 文件 | 说明 |
|------|------|
| `core/pose_compare.py` | 体式比较引擎 |
| `core/features_v2.py` | 特征提取 |
| `core/classifier_v2.py` | 学习分类器 |
| `data/asanas.json` | 体式数据库 |
| `data/models/pose_classifier_v2.pkl` | 训练好的模型 |
| `docs/yoga_research_report.md` | 研究报告 |
| `docs/yoga_pose_corrections.md` | 修正报告 |

---

## 七、版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v0.6.1 | 2026-07-19 | 新增8个体式，修正PDF错误 |
| v0.6.0 | 2026-07-18 | 学习分类器，准确率72% |
| v0.5.4 | 2026-07-17 | Bug修复 (B1-B10) |

---

## 八、参考资源

- `/Users/ching-juichang/Yoga_base_ref/PDF/` - 瑜伽资料
- `/Users/ching-juichang/Yoga_base_ref/解剖/` - 解剖图片
- `/Users/ching-juichang/Yoga_base/流瑜伽2.mp4` - 测试视频
