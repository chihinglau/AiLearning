# 真题来源检索与录入规范（R-07 配套 · v1.0）

> **文档编号**：D-10（主计划 §1.1 登记）　**定位**：D-09《考试中心与真题库设计方案》§6 留白的补齐文档。D-09 只定义“真题怎么展示、怎么卡发布”，本文定义“真题从哪来、凭什么能用、谁录谁审、按什么标准结构化”。
> **生效日期**：2026-11-14　**状态**：v1.0 已生效（CR-006 / CT-04，PM 授权执行）；配套 D-09 §5.7 审核流、`release/content-compliance/license-ledger.md` R-07 台账。
> **适用范围**：`Exam.is_past_paper = true` 的全部卷；普通卷 / 模拟卷 / 班级作业卷不受本文约束。

---

## 一、来源分层与准入白名单

只有以下四类可进入真题库。**第五类“自主题库抽题拼装”禁止标为真题**（当前 dev 库 id1~id3 即因此被降级为模拟卷）。

| 层 | 类型 | 需要的凭证 | 允许的对外表述 | `source` 取值 | 是否必须审核 |
|---|---|---|---|---|---|
| L1 | 官方公开卷（教育局 / 考试院 / 学校官网公开发布） | 发布页 URL + 页面快照 + 发布日期 | 「{地区}{年份}{年级}{学科}期末真题」 | `past_paper` | 是（双人复核） |
| L2 | 学校授权卷（校方书面授权） | 授权书扫描件 + 授权范围 + 有效期 | 「{学校}授权真题（限内部教研）」 | `past_paper` | 是 |
| L3 | 出版授权卷（教辅真题汇编） | 出版方授权书 + 图书 ISBN + 页次 | 「改编自《{书名}》（原卷为 {年份}{地区}）」 | `past_paper` | 是 |
| L4 | 改编 / 自编模拟卷 | 无（原创声明） | 只能写「模拟卷」/「仿真题」 | `mock` / `generated` | 否（`is_past_paper=false`） |
| ✗ | 自主题库抽题拼装 | — | **禁止**任何“真题”字样 | — | — |

准入判据（全部满足才可标记真题）：
1. 有可回溯的**公开发布页**或**书面授权**；
2. 卷面结构（总分 / 时限 / 题量）与原卷一致，误差为 0；
3. 卷内题干来自原卷，**不是**自主题库抽题拼装（见 §5 去重阈值）；
4. `source_name` 与台账条目可对应到唯一凭证编号。

---

## 二、检索渠道与合规边界

**允许**：
- 各级教育局、教育考试院、学校官网的“通知公告 / 招生考试”栏目公开发布的试卷与答案；
- 政府信息公开平台公开的试题；
- 已取得书面授权的学校内部卷、出版社汇编卷。

**禁止**（命中即不得入库，已有记录须下线）：
- 爬取付费题库（学科网、组卷网等付费内容）、付费公众号 / 知识星球内容；
- 教辅图书的电子版整册转载；
- 未取得授权的“名师押题卷”“内部密卷”；
- 以“网络流传”为唯一来源的卷（无发布机构、无 URL、无日期）。

**必录采集元数据**（四要素缺一不可，写入台账与 `license_note`）：
`来源 URL` + `发布机构` + `发布日期` + `采集日期`。

---

## 三、版权判定三步与 `license_note` 标准写法

### 3.1 判定三步

| 步骤 | 判断 | 结论 |
|---|---|---|
| ① 是否已公开 | 发布机构在自有渠道公开可访问 | 否则一律不得入库 |
| ② 是否事实性题目 | 数学计算、语言基础题等事实性表达 | 可合理使用，仍须登记来源 |
| ③ 是否须取得授权 | 整卷复制、含原创解析、含命题思路 | 必须取得授权书，登记编号 |

三步走完仍不确定 → **按“须授权”处理**，不进库。

### 3.2 `license_note` 三种标准模板（写库时直接套用）

```
L1 官方公开卷：公开来源：{发布机构} {发布日期}，采集于 {采集日期}，URL: {url}
L2 学校授权卷：学校书面授权：授权书编号 {编号}，授权范围 {范围}，有效期至 {日期}
L3 出版授权卷：出版方授权：授权书编号 {编号}，图书《{书名}》ISBN {isbn}，引用页次 {页次}
```

> `license_note` 属内部台账信息，**不下发学生端**（后端 `_license_note_for()` 已按 `role == "student"` 置空）；学生端仅见 `source_name`。

---

## 四、结构化录入规范

### 4.1 卷级字段（`exams` 表）

| 字段 | 要求 |
|---|---|
| `is_past_paper` | `true` |
| `source` | `past_paper`（L1~L3） |
| `source_name` | 对外来源标签，格式「{地区}{年份}{年级}{学科}{考试类型}真题」；**空值不得发布**（422 `EXAM_SOURCE_REQUIRED`） |
| `license_note` | 按 §3.2 模板填写，含凭证编号 |
| `adapted_from` | L3 或含自编解析时，写原卷标识 / 解析来源；纯原卷留空 |
| `year` / `region` / `grade` / `subject` | 必填，`year` 取原卷年份而非采集年份 |
| `exam_type` | `final`（期末）/ `midterm`（期中）/ `unit`（单元）/ `mock`（模拟） |
| `total_score` / `time_limit_min` | 与原卷完全一致 |
| `status` | 录入即 `draft`，**禁止**直接写 `published` |
| `class_id` | 必须为 `NULL`；班级派发副本由 `/api/exams/mock` 另行生成 |

### 4.2 题级字段（`questions` / 卷内 `questions[]`）

- 每题引用真实题干，`source_type = external`（原卷）或 `adapted`（改编）；
- 卷内题量与原卷一致，题序、分值按原卷；
- 自编解析单独标注，不得混入原卷题干；
- **禁止**用自主题库 `question_id` 拼装（历史错误模式：g1/g3 数学“真题”58 分 / 24 题）。

### 4.3 录入流程（状态机，与 D-09 §5.7 一致）

```
draft ──submit-review──▶ pending_review ──approve（换人复核）──▶ published
  ▲                            │
  └────────reject（必填意见）───┘
published ──offline──▶ offline ──restore──▶ draft（重走复核）
```

| 步骤 | 接口 | 卡口 |
|---|---|---|
| 1 录入 | 直接写库 / 后续录入工具 | `status=draft`，`source_name` 必填 |
| 2 提交复核 | `POST /api/exams/{id}/submit-review` | 缺来源 422 `EXAM_SOURCE_REQUIRED`；非 `is_past_paper` 404；班级副本 409 `EXAM_CLASS_COPY_NOT_REVIEWABLE` |
| 3 复核队列 | `GET /api/exams/reviews?review_status=pending_review&page=&page_size=` | 分页 + `X-Total-Count`；仅 `content:review:decide` |
| 4 通过发布 | `POST /api/exams/{id}/review {"decision":"approve"}` | 提交人＝复核人 → 409 `EXAM_REVIEW_SELF`；状态不符 409 `EXAM_INVALID_STATE` |
| 5 退回 | `{"decision":"reject","note":"…"}` | 无 note → 422 `EXAM_REVIEW_NOTE_REQUIRED` |
| 6 下线 / 恢复 | `{"decision":"offline"}` / `{"decision":"restore"}` | 下线 → `offline`；restore 回 `draft` 并清空发布留痕 |

---

## 五、与现有题库的挂接与去重

1. **归一化**：剥离册次前缀、去除标点与全半角差异（可复用 `docs/content-templates/_find_same_content.py` 的剥离法）。
2. **比对**：与库内题干做相似度比对；命中（≥0.85）则复用该题并写 `adapted_from`，未命中新建题。
3. **原卷性判定阈值**：同卷题干与自主题库重合率 **≥30%** → 判定“非原卷”，**不得**标记真题，只能落 `mock`。
4. **去重后置检查**：入库后跑一次同卷内题干重复率检查，重复率 >0 需人工复核。

---

## 六、录入—复核—发布留痕（离线台账）

`release/content-compliance/license-ledger.md` 增设「真题」分区，每条一行：

| 列 | 说明 |
|---|---|
| 凭证编号 | 唯一，例如 `SZ-2024-MATH-G3-FINAL-01` |
| 来源层 | L1 / L2 / L3 |
| 卷标识 | 年份 / 地区 / 年级 / 学科 / 类型 |
| 来源 URL 或授权书编号 | 可回溯 |
| 发布机构 / 授权方 | — |
| 发布日期 / 采集日期 | — |
| 录入人 / 录入时间 | 人 + 时间戳 |
| 复核人 / 复核时间 | **必须与录入人不同** |
| 上线时间 / 下线时间 | 含下线原因 |
| 关联 `exam_id` | 便于对账 |

**证据链验收**：任一 `published` 真题，能在台账中按 `exam_id` 反查到凭证编号、URL/授权书、录入人与复核人；缺任一项即为留痕不完整。

---

## 七、覆盖目标与缺口报表

- **首期范围**：深圳 g1–g9 语文 / 数学 / 英语，2023–2025，每科每年 ≥1 卷（共 ≥ 3×9×3 = 81 卷目标）。
- **缺口矩阵**：`GET /api/exams/past-papers/filters` 返回 `years / subjects / regions / grades / exam_types`，按「年份 × 年级 × 学科」交叉出缺口表，按缺口排采集优先级。
- **排期原则**：先补毕业年级（g6 / g9）与统考科目（语数英），再补其他年级；同一区域同年级每年不超过 3 卷，避免同质化。

---

## 八、验收指标（入库前必跑）

| 指标 | 判据 | 检查方式 |
|---|---|---|
| `source_name` 覆盖率 | 100%（`published ∧ is_past_paper`） | `select count(*) from exams where is_past_paper=1 and status='published' and (source_name is null or trim(source_name)='')` 应为 0 |
| 自造冒充 | 0 卷 | 同卷题干与自主题库重合率 ≥30% 的卷不得带 `is_past_paper=1` |
| 结构一致性 | 总分 / 时限 / 题量与原卷一致 | 逐卷人工核对 + 台账记录 |
| 解析标注 | 自编解析均标 `adapted_from` 或“解析为自编” | 文本扫描 |
| 违规表述 | 「官方」「押题」「名师」「密卷」扫描 0 命中 | 标题与描述全文检索 |
| 留痕完整 | 凭证编号 / 录入人 / 复核人齐全，且录入人≠复核人 | 台账对账 |
| 学生端泄露 | `license_note` 在学生端响应中为 `null` | 接口回归（`tests/test_exam_center.py::test_license_note_hidden_from_students`） |
| 状态机合规 | 无绕过 `draft → pending_review → published` 的记录 | `audit_logs` 中 `exam.review.*` 与状态变更对账 |

---

> **配套材料（2026-11-14 新增）**：采集执行方案 `docs/past-paper-collection-plan-20261114.md`（PA-01，覆盖矩阵 380 卷 / 分批 B1–B4 / SOP / 验收指标）；台账模板、导入结构模板与校验器 `docs/content-templates/exports/past_paper_intake_20261114/`。

## 九、与现有文档 / 代码的对应关系

| 本文条目 | 落地位置 |
|---|---|
| §1 来源分层 | `release/content-compliance/license-ledger.md` 真题分区 |
| §3 `license_note` 模板 | `backend/app/api/routes/exams.py::_license_note_for`（学生端置空） |
| §4.1 卷级字段 | `backend/app/models/exam.py`（`source_name / license_note / adapted_from`） |
| §4.3 状态机与错误码 | `exams.py`：`EXAM_SOURCE_REQUIRED` / `EXAM_REVIEW_SELF` / `EXAM_REVIEW_NOTE_REQUIRED` / `EXAM_INVALID_STATE` / `EXAM_CLASS_COPY_NOT_REVIEWABLE` |
| §5 去重 | `docs/content-templates/_find_same_content.py` |
| §7 缺口矩阵 | `GET /api/exams/past-papers/filters` |
| §8 验收 | `backend/tests/test_exam_center.py` / `test_exam_review.py` |

> 本文不定义真题的编辑加工标准（解析质量、难度标注），那部分沿用教研侧《题目入库规范》。
