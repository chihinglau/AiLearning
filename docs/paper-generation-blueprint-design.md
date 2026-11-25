# 自建题库组卷方案（单元 / 期中 / 期末）v1.3

> **背景**：真题受版权限制不可直接入库（见 `docs/past-paper-source-intake-spec.md` D-10）。替代路径：用本项目自建知识点题库，按固定蓝图规则输出**标注为“模拟卷/单元测试卷”的成套试卷**，绕开版权，支撑日常教学与练习。
> **日期**：2026-11-16　**最后更新**：2026-11-25 v1.3（按 CR-011 补「全年级按教材单元逐一出卷」发布口径，见 §〇c）
> **状态**：v1.2 已实施（81 条蓝图矩阵 + 自建题库 2322 题，**162/162 卷型全部可出卷**）；v1.3 追加 391 张按教材单元生成并发布的单元卷
> **基础**：`app/services/exam_paper.py::generate_paper`、`app/services/exam_blueprint_matrix.py`、`ExamBlueprint` 模型、`POST /api/exams/generate`

---

## 〇、PM 裁决与落地状态（2026-11-16）

| # | 裁决 | 落地方式 | 状态 |
|---|---|---|---|
| Q1 | **不接受降级卷** | 语文习作写 `q_type=composition`、英语听力写 `q_type=listening`；题库无此题型时 `generate_paper` 直接拒绝（`refused=True`），API 返回 422 `EXAM_PAPER_UNSUPPORTED` | 已实现 |
| Q2 | **期末区分上/下册** | 蓝图不绑册；新增 `scope`（unit/half_book/book）+ `textbook_id` 入参，上/下册由 `textbook_id`（含 `semester`）决定 | 已实现 |
| Q3 | **首批 g1–g9 语数英 27 组合 × 3 卷型** | `exam_blueprint_matrix.build_specs()` 生成 81 条，已写库（created=81，旧 9 条停用） | 已实现 |
| Q4 | **作废 `EXAM_TYPE_WEIGHT`** | 常量置空，回流权重统一 `1.0` | 已实现（见 §2.5 说明：该常量实为掌握度回流权重，不是题量系数） |
| Q5 | **抽检 10%** | 写入 §三 流程与 §五 验收（10% 随机抽检 + 记录 `review_note`） | 已规定 |

---

## 〇b、自建题库补量结果（2026-11-16 晚，v1.2 新增）

按“语文习作 + 英语听力/书面表达 + 数学计算题”三条线补量后，**81 条蓝图 × 2 册 = 162 卷型全部可出卷，0 拒绝**。

| 批次 | 题型 | 数量 | 入库脚本 |
|---|---|---|---|
| g1 语英数 | fill/choice/listening/composition | 386 | `seed_language_question_bank.py`、`seed_g1_chinese_bank.py` |
| g2–g9 英语 | listening | 976 | `seed_english_bank_g2_g9.py` |
| g2–g9 英语 | fill + choice + reading | 732 | 同上 |
| g2–g9 英语 | composition（16 册 × 3 篇） | 48 | 同上 |
| g2–g9 语文 | composition（16 册 × 3 篇） | 48 | `seed_chinese_bank_g2_g9.py` |
| g2–g9 语文 | fill（积累与运用，16 册 × 6） | 96 | 同上 |
| g2–g9 语文 | answer（阅读简答） | 2 | 同上 |
| g4–g9 数学 | fill 18 / answer 16 | 34 | `seed_math_supplement_g4_g9.py` |
| **合计自建** | | **2322** | 全部 `source_type=original`、`source_ref` 幂等、`status=published` |

体检（`grade_paper_audit.py --grade 1..9 --export-docs`）：各年级 18/18 OK、0 拒绝，全部 `score_matches=True`；题量语文单元 15 / 期中期末 18，数学 12 / 22，英语 28 / 39。

> 对照 §一 的原始家底：`composition` 与 `listening` 原先均为 0，是 54+ 条蓝图被拒的唯一原因；现分别为 58 与 976（含 g1）。

---

## 〇c、全年级按教材单元出卷发布口径（2026-11-25，CR-011）

> **变更来源**：PM 要求「按这个口径全年级补齐吧」——学生端不应只看到每科 1 张笼统「单元卷」，应按教材实际单元章节逐单元出卷。本节只改变**学生可见数据集的生成口径**，不改变 §二 蓝图结构、严格拒绝语义与 §三 出卷流程；对应主计划 CR-011 / L37 / §6.34。

| 项 | 口径 |
|---|---|
| 覆盖范围 | 1–9 年级 × 语文/数学/英语 × 上/下册；9B「待发布」占位章节不铺题、不生成 |
| 单元切分 | `scripts/generate_all_unit_papers.py::split_units()` 从章节名解析「第 N 单元 / 第 N 章 / Unit N / 中文数字开头」，同名单元起至下一单元前的章节合并为一个单元范围 |
| 出卷方式 | 每个单元一张卷，标题 `N年级X科上/下册 第k单元卷（章节名）`；调用 `POST /api/exams/generate`，`blueprint_code=g{grade}_{subject}_unit`，`chapter_ids=单元章节`，`seed` 固定可复现 |
| 严格门禁 | `allow_fallback=False` 不放宽题型；`allow_band_relax=True` 允许难度带内补位；最多 8 个候选 seed 重试；`avoid_recent_repeats=False` 与干跑口径一致，避免补量轮被历史卷排重误伤 |
| 题库补量 | ① `backfill_unit_question_bank.py` 补 7–9 年级英语各单元 8 道原创听力及低年级缺口 1 道，共 321 道；② `backfill_unit_paper_supplements.py` 按 `shortages` 动态补 choice/fill/answer/composition/listening 共 335 道。全部 `source_type=original`、`source_ref` 幂等、无第三方版权素材 |
| 幂等 | 同标题卷已存在即跳过；重复执行 `--apply` 只补缺失单元，不覆盖已发布卷 |

**执行结果（dev 库，2026-11-25）**

| 指标 | 结果 |
|---|---|
| 干跑 | `planned=391 skipped=0 succeeded=0 failed=0 dry_run=True` |
| 正式生成 | `planned=391 skipped=0 succeeded=391 failed=0 dry_run=False` |
| 新增卷 | **391 张**，标题均带「第 N 单元卷（章节名）」 |
| 存量卷 | 27 张旧版笼统「N年级X科单元卷」在 CR-011 时保留；2026-11-25 用户决策 CR-012 已全部置 `offline`（作答记录保留），见主计划 §6.34.6 |
| 发布后单元卷 | CR-011 时 published **418 张** = 391 新 + 27 旧；2026-11-25 用户决策 CR-012 已把 27 张旧卷全部下线，最终 published **391 张**（全部为按教材单元新卷），详见主计划 §6.34.6 |
| 快照完整性 | 空 `questions` 快照 **0**；快照中的题目 ID 在 `questions` 表全部存在（缺失 0） |
| 学生可见性 | 418 张均满足 `status=published`、`is_past_paper=0`、`source!='assignment'`、`class_id is NULL`；学生接口按 `grade/subject/type=unit` 可见（g8 英语实测 17 张，年级均为 8） |

**备份与脚本**

- 生成前备份：`backend/ailearning_dev.db.bak-20261125-before-all-unit-papers`；英语卷修复前备份：`backend/ailearning_dev.db.bak-20261125-before-en-paper-repair`。
- 保留脚本：`scripts/generate_all_unit_papers.py`、`scripts/backfill_unit_question_bank.py`、`scripts/backfill_unit_paper_supplements.py`、`scripts/repair_g8_english_papers.py`。
- 旧版 27 张笼统卷已按用户 2026-11-25 决策登记 **CR-012** 并全部下线（`offline`），作答记录保留；详见主计划 §6.34.6。

---

## 一、题库家底审计（2026-11-16 实测，dev 库）

| 指标 | 数值 | 说明 |
|---|---|---|
| 题目总数 | **12,278** | 有效年级（g1–g9）**12,116** |
| 知识点 / 章节 / 教材 | 3,366 / 726 / 146 册 | g10–12 每科仅 6 题，属残留数据，不参与组卷 |
| 年级-学科组合 | **46** | g1–g9 × 各科 |
| 每组合题量 | 139 ~ 443 | 最少 g7 历史 139、g9 道法 146 |
| 题型 | `choice` / `fill` / `answer` / **`judge` / `multiple`** | **无 composition（作文）、无 listening（听力）、无 experiment** |
| 难度分布 | easy 0~15（多数组合 0）、medium 70–85%、hard 15–25% | 用绝对难度值切档会严重退化，见 §2.3 |
| 章均题量 | **14 ~ 20 题/章**（每册 7~14 章） | 单元卷范围需按“3 章折算 1 单元”解析 |

**容量核算**（`exports/paper_blueprint_20261116/bank_capacity_20261116.csv`）：期末 25 题门槛 **46/46 达标**；按 6:3:1 难度配比仅 **1/46 达标**（easy 池近乎为空）→ 必须改口径，不能直接用现有难度标签。

---

## 二、卷型规则

### 2.1 范围与规模

| 卷型 | scope | 题量 | 总分 | 时长 | 覆盖下限 |
|---|---|---|---|---|---|
| 单元测试卷 | `unit`：该单元章节（无“第N单元”命名时按 **3 章折算 1 单元**） | 13–15 | 60 | 40 min | 章节覆盖 ≥ 90% |
| 期中模拟卷 | `half_book`：册前半章节 | 22 | 100 | 小学 60 / 初中 90 min | ≥ 80% |
| 期末模拟卷 | `book`：全册 | 22 | 100 | 小学 90 / 初中 120 min | ≥ 80% |

> 覆盖口径：**取「知识点覆盖」与「章节覆盖」的较大者**校验。分母只算题库确有可用题目的章节，避免占位章节永久压低覆盖率；一张 22 题期末卷不可能覆盖全册上百个知识点，以章节覆盖为达标口径。

### 2.2 结构模板（见 `app/services/exam_blueprint_matrix.py`）

| 学科 | 单元卷（60 分） | 期中/期末（100 分） |
|---|---|---|
| 数学 | 选择 4×4 + 填空 5×4 + 解答 3×8 = 60 | 选择 10×3 + 填空 6×3 + 计算 4×8 + 综合 2×10 = 100 |
| 语文 | 积累 8×2 + 选择 4×3 + 阅读 2×10 + **习作 1×12（composition）** = 60 | 积累 16 + 选择 18 + 阅读 36 + **习作 30（composition）** = 100 |
| 英语 | **听力 8×1（listening）** + 选择 8×2 + 填空 8×2 + 阅读 4×5 = 60 | **听力 10×2** + 选择 24 + 填空 20 + 阅读 18 + 书面表达 18 = 100 |

### 2.3 难度口径：题型池内排名分位

1. 每个大题只看**同题型**的候选池；
2. 池内按 `difficulty` 升序排名，低 **60%** → easy、中 **30%** → medium、高 **10%** → hard；
3. 分位不足时允许**放宽难度带**（同题型补位），但**绝不放宽题型**——缺 composition/listening 就拒绝出卷。

按排名切分而非按 difficulty 数值切分，是因为题库 difficulty 集中在 2–3，按数值切会让三档退化成一档。实测出卷难度分布已接近 6:3:1。

### 2.4 硬约束（已实现）

| # | 规则 | 实现 |
|---|---|---|
| R1 | 卷内不重复题 | `used` 集合 + head/candidates 去重 |
| R2 | 同一大题内同一知识点 ≤2 题；整卷 ≤4 题（题量需求大时按 `ceil(题量/知识点数)` 动态放宽） | `KP_CAP_PER_SECTION` / `KP_CAP_PER_PAPER` / 动态 `kp_cap` |
| R3 | 逐题分值合计必须 = 蓝图总分，否则拒绝 | 生成后校验 |
| R4 | 排除 `status != published`、`answer` 为空的题 | 池构造时过滤 |
| R5 | `seed` 可复现 | `random.Random(seed)` |
| R6 | 章节覆盖优先（每章先取 1 题，再补知识点覆盖） | `_pick` 三段式 |
| R7 | 普通卷标题不得含“真题”，生成卷 `source=generated`、`is_past_paper=false` | API 校验 `EXAM_TITLE_MISLEADING` |
| R8 | 不足即拒绝，不静默兜底（`allow_fallback` 仅保留给历史测试/迁移场景） | `ExamPaper.refused` / `shortages` |

### 2.5 关于 `EXAM_TYPE_WEIGHT`（重要澄清）

原常量 `EXAM_TYPE_WEIGHT = {"unit":0.8,"midterm":0.6,"final":0.5}` 实际用途是**掌握度回流权重**（交卷/自评时写 `StudentQuestionRecord.kp_weight`），**不是**组卷题量系数。按 PM “作废”裁决已置空，回流统一按 `1.0`；出卷题量完全由蓝图 `sections` 决定，两者不再互相干扰。若后续希望“期末比单元测更能影响掌握度”，需重新定义依据（如按题目难度或卷面权重），不能再用拍脑袋的 0.8/0.6/0.5。

---

## 三、出卷流程

1. 选年级 + 学科 + **学期（上/下）** + 卷型（+ 单元序号）；
2. `POST /api/exams/generate`，传 `blueprint_code` + `textbook_id` + `scope`（+`unit_index`）；兼容旧调用仍可传 `chapter_ids`；
3. 返回预览字段：题量、总分、`kp_coverage`、`difficulty_mix`、`refused`、`refuse_reason`、`shortages`；
4. 被拒绝时 422 `EXAM_PAPER_UNSUPPORTED`，附缺口清单（哪一节、要多少题、题库有什么题型），不落库；
5. 通过后 `Exam(status=published, source=generated)`；
6. **抽检 10%**（已实现 PG-05）：`GET /api/exams/review-sampling?ratio=0.1&seed=...` 稳定随机抽卷（同 seed 结果一致）；`POST /api/exams/{id}/sample-review` 登记结论——通过写 `reviewed_by/reviewed_at` 与 `[抽检通过]` 留痕，不通过回 `draft` 并写 `[抽检退回]` 意见；首批仍建议 100% 抽检，稳定后降档 10%。

---

## 四、实施结果（2026-11-16）

### 4.1 代码变更

| 文件 | 变更 |
|---|---|
| `backend/app/services/exam_paper.py` | 重写选卷内核：题型池内排名分位难度带、published/answer 过滤、章节覆盖优先、动态 KP 上限、严格拒绝、分值校验、`resolve_scope_chapters`（unit/half_book/book） |
| `backend/app/services/exam_blueprint_matrix.py` | 新增：81 条蓝图矩阵 + `apply_matrix`（幂等 upsert + 停用旧 9 条） |
| `backend/app/api/routes/exams.py` | `generate_exam` 接入 scope 解析、拒绝语义（422 `EXAM_PAPER_UNSUPPORTED` + shortages）、标题合规校验；`EXAM_TYPE_WEIGHT` 置空、回流权重 1.0 |
| `backend/app/schemas/exam.py` | `ExamGenerateIn` 增 `textbook_id/scope/unit_index`（`chapter_ids` 改可选）；`ExamGenerateOut` 增 `refused/refuse_reason` |
| `backend/scripts/seed_exam_blueprint_matrix.py` | 干跑/`--apply` 写库，附带题型供给诊断 |
| `backend/scripts/dry_run_paper_matrix.py` | 用真实题库对 81 条蓝图逐条试跑，输出可出卷/拒绝清单 |

### 4.2 库变更

- 备份：`backend/build/backups/ailearning-backup-20261116-090246-pre-pg-matrix.db`
- 写入：81 条矩阵蓝图（`created=81`），旧 9 条（`math_primary_*` 等）置 `is_active=False`（`deactivated=9`）。

### 4.4 配套接口（PG-05，P1）

| 方法 | 路径 | 用途 | 权限 |
|---|---|---|---|
| POST | `/api/exams/generate` | 组卷；新增 `avoid_recent_repeats`/`exclude_question_ids`，返回 `excluded_recent_count`/`excluded_manual_count` | `content:exam:write` |
| GET | `/api/exams/{id}/spec-table` | 双向细目表（计划 vs 实际、题型、难度带、知识点、章节） | `content:exam:write` |
| GET | `/api/exams/{id}/answer-sheet` | A4 答题卡 HTML（不含题干/答案） | `content:exam:write` |
| GET | `/api/exams/review-sampling` | 抽检抽样（`ratio` 默认 0.1，`seed` 可复现，只抽未复核） | `content:exam:write` |
| POST | `/api/exams/{id}/sample-review` | 登记抽检结论（通过留痕 / 不通过回 `draft`） | `content:exam:write` |

成卷导出脚本：`backend/scripts/sample_paper_docs.py --blueprint <code> --grade N --scope unit|half_book|book [--unit-index N]`，产出 `paper.html`（学生版）、`paper_teacher.html`（含答案与解析）、`answer_sheet.html`、`spec_table.json`、`summary.json`。

### 4.3 真实题库干跑结果（`dry_run_paper_matrix.py`）

| 学科 | 可出卷 | 拒绝 | 拒绝原因 |
|---|---|---|---|
| 数学 | 23 / 27 | 4 | g4/g5 的单元卷与期中卷：题型供给不足（该册 choice/fill/answer 余量低于蓝图） |
| 语文 | 0 / 27 | 27 | 题库缺 `composition`（习作）——按 Q1 口径拒绝 |
| 英语 | 0 / 27 | 27 | 题库缺 `listening`（听力）——按 Q1 口径拒绝 |
| **合计** | **23 / 81** | **58** | |

> 结论：**数学 23 条现在就能出成套卷**；语文/英语必须先补“习作/听力”题型内容，否则按 Q1 口径一律不出卷（这是用户明确选择的“宁缺不降级”）。

---

## 五、验收指标

| # | 指标 | 阈值 | 校验 |
|---|---|---|---|
| 1 | 分值自洽 | 逐节合计 = `total_score` | `test_exam_blueprint_matrix.py` + 生成后校验 |
| 2 | 覆盖达标 | 单元 ≥90%、期中期末 ≥80%（知识点/章节取大） | 返回 `kp_coverage` |
| 3 | 难度配比 | 三档齐全、题量合计 = 卷面题量 | 返回 `difficulty_mix` |
| 4 | 拒绝语义 | 缺题型/题量不足必须 422，不落库 | `test_refuses_when_question_type_missing` |
| 5 | 重复控制 | 卷内无重复；同大题同知识点 ≤2 | `test_generate_paper_matches_blueprint` |
| 6 | 命名合规 | 生成卷标题 0 处“真题” | API 校验 |
| 7 | 可复现 | 同 seed 两次完全一致 | `test_generate_paper_is_deterministic_per_seed` |
| 8 | 抽检 | 每批 10% 抽检留痕 | 流程要求（人工） |

复验命令：

```powershell
Push-Location D:\ai\prj\trae\HuaWei\AiLearning\backend
& .venv\Scripts\python.exe -m pytest -q tests/test_exam_paper.py tests/test_exam_blueprint_matrix.py
& .venv\Scripts\python.exe scripts\seed_exam_blueprint_matrix.py          # 干跑看题型供给
& .venv\Scripts\python.exe scripts\dry_run_paper_matrix.py                # 真实题库逐条试跑
Pop-Location
```

---

## 六、遗留与下一步

| # | 事项 | 处理建议 |
|---|---|---|
| 1 | 语文“习作”、英语“听力”题型缺失 | **已完成**：g1–g9 语文习作 54 篇（g1 6 + g2–g9 48）、英语听力 976 题、英语习作 52 篇；162/162 卷型可出卷 |
| 2 | 数学 g4/g5 单元/期中供给不足 | **已完成**：g4 上 / g5 上各补 6 道计算解答，g4–g9 补 18 填空 + 16 解答，数学 g1–g9 全部 18/18 OK |
| 3 | 题库 `difficulty` 标签失真（easy 近乎为 0） | 排名分位已规避该问题；长线建议 3 档重标（1/3/5）+ 抽样校准 |
| 4 | 双向细目表、答题卡导出 | **已完成（PG-05）**：`GET /api/exams/{id}/spec-table`、`GET /api/exams/{id}/answer-sheet`（A4 打印 HTML，不含题干与答案） |
| 5 | 跨卷重题去重 | **已完成（PG-05）**：生成时默认排除同年级同学科同卷型最近 3 张卷题号（`avoid_recent_repeats=true`），可用 `exclude_question_ids` 追加手动排除 |
| 6 | 教师端组卷工作台（预览/换题/锁定） | P2 待做 |
| 7 | 期末卷「覆盖」指标读法（曾记为 0.36–0.71） | **已澄清为口径问题并给出归一指标**：`chapter_coverage` 162 卷平均 **0.999**、<0.6 共 0 卷；0.36–0.71 实为 `kp_coverage`，因一题只挂 1 个知识点，覆盖率上限 = `min(知识点池, 题量)/知识点池`（g4 数学上 0.44、g6 数学上 0.41、g5 数学上 0.44，实测已触及上限）。已新增 `kp_coverage_cap` 与 `kp_coverage_normalized`（实测/上限），归一后全库平均 **0.941**、<0.6 为 **0 卷**、<0.8 为 **10 卷**（全部是数学期中/期末）。代码 `exam_paper.py:406-410` 双口径并存、拒绝阈值取 `effective_coverage = max(kp, chapter)`，期末卷按章节覆盖判定达标。逐章节核查亦证明「末几单元靠原库题支撑」不成立（每章 18–20 题、分布均匀），**补章节语料无法提升该指标** |
| 8 | 语文「积累与运用」逐单元对齐 | **已完成（v2.09）**：按「每章 4 条、2 章=1 单元凑 8 条」生成并入库 **616 条**（`selfbank:zh_fillu:*`），另补 `topup_zh_fills.py` 48 条补齐单章即单元的册；配套每单元 1 条带三维量规习作（130 条）与每单元 1 篇原创短文 + 2 问的阅读题（260 条）。新增 `unit_paper_audit.py` 逐单元体检：语文单元卷 **216/216 OK**（此前仅第一单元可出卷、18/216）。全库单元级体检三科 648 卷中 OK 312、剩余 336 缺口全部在数学与英语 |
| 9 | 习作评分点仅 3 条通用维度 | **已完成**：升级为中考三维分档量规（内容 40% / 结构 30% / 语言 30%，各一/二/三档），54 题 `content.rubric` + `answer.rubric` 全量更新（`scripts/upgrade_zh_alignment_rubric.py`） |

---

## 七、与现有文档的关系

| 文档 | 关系 |
|---|---|
| `docs/exam-center-and-past-papers-design.md`（D-09） | 考试中心与审核流；自建卷为普通卷，生成即 `published`，不进真题库 |
| `docs/past-paper-source-intake-spec.md`（D-10） | 真题准入；本方案产物不得标 `is_past_paper` |
| `exports/paper_blueprint_20261116/bank_capacity_20261116.csv` | 46 组合容量核算，蓝图参数依据 |

---

## 八、v1.3 落地状态（2026-11-18/19 实测口径）

> 本节是「蓝图 → 库里真实可开考的卷」的最终对齐结果。前面的 §2 卷型规则是**能力矩阵**（162 卷型可出卷），本节是**实际上架的 81 张**。

### 8.1 上架规模（dev 库实测）

| 项 | 实测值 |
|---|---|
| published 且 `class_id is null` | **81 张** |
| 按年级分布 | g1–g9 各 **9 张**（语文/数学/英语 × 单元/期中/期末） |
| 重复组 | 0（81 张对应 81 组，无同组并存） |
| 真题（`is_past_paper=1` 且 published） | **0 张** —— 自建题库口径，不接版权真题 |

从 162 卷型到 81 张上架的过程做了两件事：① 删掉 10 张 g6 早期重复卷，7 组「走查卷 + 早期正式卷」并存时保留题量更足的一张；② 卷名统一为 `{年级}年级{科目}{阶段卷}`，清掉「走查卷」「自建题库」等内部流程词。

### 8.2 卷型实测题量

| 阶段 | 语文 | 数学 | 英语 | 分值 / 时限 |
|---|---|---|---|---|
| 期末 | 28 | 25 | 39 | 100 分 / 90 分钟 |
| 期中 | 24 | 22 | 39 | 100 分 / 60 分钟 |
| 单元 | 15 | 12 | 28 | 60 分 / 40 分钟 |

1–9 年级题量完全一致，故 81 张卷总题量 = 9 × (28+25+39 + 24+22+39 + 15+12+28) = **2088 题**（实测快照一致）。

### 8.3 听力配比修复（CR-008 收尾）

旧组卷在英语卷里只按题型池随机取，出现过「卷面标了听力分节、实际没进听力题」的情况。修复后英语每张卷固定含听力分节，且听力题音频必须可取（`kind=listening`）。这一条已纳入开考实测的断言：81 张卷里「英语听力音频非 200」计数为 **0**。

### 8.4 质量流水线（四层，全绿）

| 层 | 脚本 | 结果 |
|---|---|---|
| 数据体检 | `audit_published_papers.py` | 81 卷：7 类硬问题 **0**，`LEAK_INFO` 16 |
| 开考实测 | `verify_papers_takeable.py` | **81/81 开考 200**，空卷 0，首题空 0 |
| 形态走查 | 真机 g1–g9 | 卷名/学科/题量/满分/时限全部一致 |
| 题目快照 | `snapshot_papers.py` | 2088 题，8 类机检 **0 异常** |

产物位置与用法见 `k12-learning-app-design.md` §5.3 与 `exports/paper_audit_20261118/README.md`。

### 8.5 此前提到的两项指标现状

- `kp_coverage` 的「0.36–0.71 偏低」已按 §6 第 7 条澄清为口径问题，归一后 `kp_coverage_normalized` 全库平均 0.941、<0.6 为 0 卷，**不需要**靠补末几单元语料来抬。
- 期末卷改按 `chapter_coverage` 判定达标（162 卷型平均 0.999），期末卷不再以 kp 指标卡发布。

