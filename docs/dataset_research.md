# 公开瑜伽体式数据集调研（用于完善体式数据库）

> 目标：为 `data/asanas.json` 的**扩库**与 **rules 目标角/容差校准**找到可落地的公开数据源。
> 本软件的比对引擎使用 MediaPipe world landmark 的角度/朝向/垂直关系（视角无关），
> 因此最契合的数据是「能跑 MediaPipe 提取骨架、并带体式标签」的图像或已算好的角度。

---

## 1. 候选数据集对比

| 数据集 | 规模 | 内容 | 许可 | 对本项目的用处 | 风险 |
|---|---|---|---|---|---|
| **Yoga-82** (Verma et al., 2020, arXiv:2004.10362) | 28.4K 图 / **82 体式** / 三级层级(6·20·82) | 网络抓取图像 + 标签 + train/test 切分链接 | **非商业研究/教育** | 体式**覆盖清单**（82 个名字）与分类标签；可作为扩库的「还缺哪些体式」清单 | 图像视角/遮挡/光照杂，直接跑 MediaPipe 噪声大；仅限非商业 |
| **Yoga_Pose_Detection** (vishwasbhairab, GitHub) | 复用 Yoga-82 | 含**图像下载器** + PyTorch 82 类分类器(89% acc) | 继承 Yoga-82 条款 | 参考「抓取→MediaPipe→训练」管线 | 同上许可 |
| **Yoga82** (Anandkumar8418, GitHub) | 复用 Yoga-82 | 用 **MediaPipe 提取关节角 → CSV**；TF 分类 96% | 继承 Yoga-82 条款 | 证明「MediaPipe 角度」可用来刻画体式，方法可直接借鉴 | 同上许可 |
| **Yoga_Poses-Dataset** (Manoj-2702, GitHub) | 多体式 | **MediaPipe 提 landmark + 算角度**，含图像/landmark/角度 | **MIT（宽松）** | 最契合：可直接取其角度 CSV 作为 `rules.target/tol` 的参考真值来校准 | 体式覆盖有限，需按需取子集 |

关键结论：
- **扩库清单** → 以 Yoga-82 的 82 体式名为「还缺什么」的对照表（本库当前 14 体式，缺大量坐/卧/倒立/手臂平衡类）。
- **校准真值** → 优先用 **Manoj-2702（MIT）** 的角度数据，或自己用 `tools/calibrate_from_images.py` 从教练照片/公开 CC 图提取（方法同 Anandkumar8418）。
- **非商业限制**：Yoga-82 系列仅限研究/教育，若本工具未来商业化需替换为自采或 MIT 数据。

---

## 2. 推荐落地路径（与计划书 §5 对齐）

1. **扩库（P2-6）**：从 Yoga-82 的 82 体式名中挑选高频基础体式，按现有 schema 手工补 `joint_angle`/`bone_orientation`/`vertical_order` 规则（同 12 体式做法，启发式默认目标）。
   - 已补：v0.4.0 新增 **手倒立式(handstand)**、**乌鸦式(crow)**，并新增 `vertical_order` 规则类型以区分倒立/手臂支撑与站姿。v0.5.0 续补坐姿（坐立前屈 paschimottanasana、坐角式 upavistha_konasana）、俯卧（蝗虫式 salabhasana、弓式 dhanurasana、鳄鱼式 makarasana）、平衡（舞王式 natarajasana、鹰式 garudasana、轮式 urdhva_dhanurasana、前臂倒立 pincha_mayurasana），标准库共 **23 体式**；并为消除 argmax 误判，给多个体式增补判别规则（脚在髋下 / 双臂皆上举 / 单腿支撑等），详见 `tests/test_expand.py`。
   - v0.5.1 新增 **站立手抓大脚趾式(extended_hand_to_toe)**；针对侧脸/强透视导致 world landmark 失准的问题，引擎新增 `image_angle` / `image_distance` / `image_vertical_order` 三类**图像空间规则**，与 world 规则混合使用。标准库共 **24 体式**。
2. **校准（P1-5 / P2-8）**：用 `tools/calibrate_from_images.py`
   - 输入：`data/ref/<asana_id>/` 下放参考图（jpg/png，跑 MediaPipe）或直接放 `landmarks.json`（world landmark 数组）。
   - 输出：`data/asanas.suggested.json`（仅更新有参考样本的 rule 的 target/tol/min_sep），**人工复核后**再并入 `asanas.json`。
   - 这实现了计划书 §5.2 的「录制工具：从标准视频/照片提取 landmark 自动生成参考」。
3. **提升自动识别精度（P1-5）**：扩库后 `detect_asana` 的 argmax 覆盖更全；仍建议用真人/标准照片样本校准各体式 tol，避免「全绿但明显不对」。

---

## 3. 引用（若使用对应数据集请致谢原作者）

- Verma, Kumawat, Nakashima, Raman. *Yoga-82: A New Dataset for Fine-grained Classification of Human Poses.* arXiv:2004.10362 (2020). https://sites.google.com/view/yoga-82/
- Manoj-2702/Yoga_Poses-Dataset (MIT). https://github.com/Manoj-2702/Yoga_Poses-Dataset
- Anandkumar8418/Yoga82. https://github.com/Anandkumar8418/Yoga82
- vishwasbhairab/Yoga_Pose_Detection. https://github.com/vishwasbhairab/Yoga-Pose-Detection

---

## 4. 备注

- 本调研仅做「数据源定位与方法可行性」，**未在本仓库内打包任何第三方图像**（许可与体积考量；`data/models/*.task` 与 `data/uploads/*` 已在 .gitignore 排除）。
- 校准工具默认 `data/ref/` 不入 git；用户自采的教练照片放此处即可，不会污染版本库。

---

## 5. 第二轮全网搜索增补（2026-07-11）

> 本轮目标：找**直接契合 MediaPipe 33 点**的骨架/角度数据（用于校准 `rules.target/tol`）、**大规模体式覆盖清单**（扩库候选）、**专业参考图库**（人工补规则+顺位要点）、**中文对照资源**（UI 标签）。
> 背景：用户实测两张图，其中「一膝跪地+另一腿前伸的侧弯/低弓步」被 `detect_asana` 误判为 camel（当前库 24 体式缺门闩式/低位弓步），印证扩库优先级。

### 5.1 直接契合 MediaPipe 的关键点/角度数据集（首选校准源）

| 数据集 | 关键点 | 规模 | 许可 | 对本项目用处 |
|---|---|---|---|---|
| **Kaggle「keypoints of yoga poses」**(suhaniajaythakur, 2024-12) | **33 点**，与 MediaPipe 完全对齐 | 多体式 | 待核查（Kaggle 默认 CC/BY 类，需逐页确认） | 直接提取骨架角/朝向真值，喂给 `tools/calibrate_from_images.py` |
| **PosePilot** (gadhvirushiraj, GitHub + DeepWiki) | MediaPipe 33 点逐帧 CSV (x,y,z,visibility) | 336 视频 = 6 体式 × 4 视角 × 14 人 | 待核查 | 多视角时序骨架，最适合做 per-体式 `tol` 真值；含视频逐帧 landmark |
| Manoj-2702/Yoga_Poses-Dataset（§1 已列） | MediaPipe landmark + 角度 CSV | 多体式 | **MIT** | 已收录，最稳的宽松许可真值源 |

### 5.2 大规模图像分类数据集（体式覆盖清单）

| 数据集 | 规模 | 许可 | 用处 |
|---|---|---|---|
| **Yoga-82 2026 新版**（Kaggle: rashiniyasp/yoga-82-2026；Harvard Dataverse 镜像 doi:10.7910/DVN/FX3DIE） | 82 体式，持续更新 | 非商业研究/教育 | 覆盖清单 + 参考图（非商业限制同 §1） |
| **yoga-poses-dataset**（Kaggle） | **107 体式 / 5994 图**，每类~60 | 待核查 | 扩库候选清单，体式覆盖最全 |
| **3000 张多类别瑜伽体式图像**（CSDN, 2024-11, 446.5MB） | 3000 图，梵英双语标注 + URL 元数据 | 待核查 | 带双语标签的覆盖清单 |
| **In-house Yoga Pose Dataset**（10 体式） | 27 人，1080p/4K 视频 | 自采自愿 | 可作自采样本范式（Malasana / Ananda Balasana / Janu Sirsasana / Anjaneyasana / Tadasana / Kumbhakasana / Hasta Uttanasana / Paschimottanasana / Uttanasana / Dandasana） |

### 5.3 专业参考图库（人工补规则 + 顺位要点）

| 来源 | 内容 | 获取 |
|---|---|---|
| **Yoga Journal Pose Finder (A-Z)** | 权威 A-Z 体式，含英文/梵文/类型/禁忌/分步 | 会员制（仅参考，不可打包） |
| **Yoga Paper**（40 Hatha / 215 Hatha cheat sheet） | 简笔 stick-figure + 中英梵名 | 部分免费样本下载 |
| **WorkoutLabs（146 poses）** | 图片 + 梵文发音 + 分步 + 益处 + 变体 + 禁忌 | 免费在线指南 |
| **houseofomyogaschool Glossary PDF** | 图片 + 类型 + 脉轮 + 能量属性 | 公开 PDF |

### 5.4 中文对照资源（中英梵，便于中文 UI 标签）

- **Hello Yogis 100+ 体式库**（中/英/梵 + 步骤，v0.4 已引用）
- **Bilibili 常见体式中英梵对照图**（参考《瑜伽之光》命名）
- **topyogaworld 100 poses**（中英梵对照清单）

### 5.5 候选入库体式（基于缺口分析）

当前库 24 体式：`downward_dog, tree, triangle, warrior2, warrior3, chair, plank, bridge, cobra, camel, boat, handstand, crow, paschimottanasana, upavistha_konasana, salabhasana, dhanurasana, makarasana, natarajasana, garudasana, urdhva_dhanurasana, pincha_mayurasana, extended_hand_to_toe`（+ 1 待确认，共 24）。

对比高频基础体式清单（WorkoutLabs / Yoga Journal / Yoga Paper），优先补：

**P2-高（与用户实测误判直接相关，建议最先补）**
- ✅ `gate`（门闩式 Parighasana）— **v0.5.3 已入库**
- ✅ `low_lunge`（低位弓步 Anjaneyasana）— **v0.5.3 已入库**
- `warrior1`（战士一式 Virabhadrasana I）— 原本已在 24 体式库中，非新增
- ✅ `side_angle`（侧角式 Utthita Parsvakonasana）— **v0.5.3 已入库**

**P2-中（高频基础）**
- `mountain`（山式 Tadasana）
- `half_moon`（半月式 Ardha Chandrasana）
- `revolved_triangle`（扭转三角 Parivrtta Trikonasana）
- `reverse_warrior`（反战式 Viparita Virabhadrasana）
- `child`（婴儿式 Balasana，修复）
- `sphinx`（狮身人面式 Salamba Bhujangasana）
- `pigeon`（鸽王式 Eka Pada Rajakapotasana）

**P2-低（倒立/坐姿/平衡扩展）**
- `headstand`（头倒立 Sirsasana）、`shoulder_stand`（肩倒立 Sarvangasana）、`plow`（犁式 Halasana）、`fish`（鱼式 Matsyasana）
- `lotus`（莲花坐 Padmasana）、`easy`（简易坐 Sukhasana）、`bound_angle`（束角式 Baddha Konasana）
- `side_plank`（侧板式 Vasisthasana）、`dolphin`（海豚式 Ardha Pincha Mayurasana）、`lizard`（蜥蜴式 Utthan Pristhasana）、`happy_baby`（快乐婴儿式 Ananda Balasana）

### 5.6 落地建议

1. **P2-高已完成入库（v0.5.3）**：`gate`（门闩式）、`low_lunge`（低位弓步）、`side_angle`（侧角式）已写入 `data/asanas.json`，标准库 24 → 27 体式。注意 `warrior1`（战士一式）**原本就在 24 体式库中**，并非本轮新增 id，故净增 3 体式。下一轮可继续 P2-中（mountain / half_moon / revolved_triangle / reverse_warrior / child / sphinx / pigeon）。
2. 校准真值优先用 **MIT 的 Manoj-2702** 与 **Kaggle 33-keypoint**（若许可允许）；避免直接打包 Yoga-82 非商业图。
3. **许可核查**：Kaggle / CSDN 数据集需逐一下载页确认 license 字段；不确定的一律只取「角度/骨架」而非图像，或仅作覆盖清单。

---

## 6. 引用（增补）

- suhaniajaythakur/keypoints-of-poses (Kaggle, 2024). https://www.kaggle.com/datasets/suhaniajaythakur/keypoints-of-poses
- gadhvirushiraj/PosePilot (GitHub). https://github.com/gadhvirushiraj/PosePilot  · DeepWiki 数据集文档 https://deepwiki.com/gadhvirushiraj/PosePilot/5-dataset
- rashiniyasp/yoga-82-2026 (Kaggle, 2026). https://www.kaggle.com/datasets/rashiniyasp/yoga-82-2026
- Yoga-82 Harvard Dataverse 镜像. https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/FX3DIE
- yoga-poses-dataset (Kaggle, 107 poses / 5994 imgs). https://www.kaggle.com/datasets (搜索 "yoga poses dataset 107")
- 3000 张多类别瑜伽体式图像数据集 (CSDN, 2024-11). https://wenku.csdn.net/doc/3k5vcj0b83
- Yoga Journal Pose Finder. https://yogajournal.com/pose-finder
- Yoga Paper 40 Hatha Poses. https://yogapaper.com/40-hatha-yoga-poses/
- WorkoutLabs Yoga Poses Guide (146). https://workoutlabs.com/yoga-poses-guide
- houseofomyogaschool Yoga Glossary PDF. https://houseofomyogaschool.com/wp-content/uploads/2023/05/Yoga-poses-Glossary-Sheet1.pdf
- Hello Yogis 体式大全. https://helloyogis.com/magazine/2022/06/27/all-asana
- topyogaworld 100 Yoga Poses. https://www.topyogaworld.com/archives/3365
