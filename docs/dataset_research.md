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
