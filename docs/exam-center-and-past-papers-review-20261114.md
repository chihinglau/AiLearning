# D-09 考试中心与真题库方案 · 评审报告（含真题教研数据来源检索评估）

> **评审对象**：`docs/exam-center-and-past-papers-design.md`（D-09）。第一轮对象 v1.0「已生效 · 已实施」，456 行 / 36.6 KB，mtime 14:56；第二轮对象 **v1.1「已生效 · 待更新」（CR-005 后续项转正）**，mtime 15:58
> **评审日期**：2026-11-14（第一轮 15:29；**第二轮复核 15:30 之后，结论见 §一·二**）
> **评审性质**：文档评审 + 实现一致性核对（**两轮均为只读**：第一/二轮未改代码、未改库、未改 D-09 文档；**§九 为第三段——PM 授权后按评审意见实施**，属实施记录而非评审动作）
> **评审结论（最新，第二轮）**：**设计层面通过（v1.1 审核流设计合理）；实现层面由“不可用”改善为“可用但有数据污染”；合规层面仍未闭环；真题来源检索规范仍缺**
> **实施状态（第三段，2026-11-14 16:11 起）**：数据口径与 P1 代码加固**已落地并全绿**（后端 443 passed / 前端 175 passed），详见 **§九**；未闭环项见 §9.5
> **第一轮结论（历史）**：设计层面通过；实现一致性不通过；真题数据来源检索方案缺失
> **复核方式**：读全文 + 直连 `backend/ailearning_dev.db` + ORM 探针 + Alembic 版本核对 + 代码逐行核对 + 实跑 `pytest` 审核子集（证据见附录 A / §一·二）

---

## 一、结论摘要

1. **考试中心与真题库的“页面级设计”是完备的**：§4.4「状态 × 窗口」矩阵是唯一决策表，六种组合各有唯一按钮与明确反馈；筛选维度、卡片字段、空态异常、权限到元素、兼容策略（可选参数 + 响应体保持数组 + `X-Total-Count` 走头）均可直接用于验收。这一部分**建议维持 v1.0 已生效状态**。
2. **但“已实施”与运行现状不一致**：dev 库的 Alembic 版本停在 `a2b3c4d5e6f7`，head 为 `b4c5d6e7f8g9`，`exams` 表缺 `source_name / license_note / adapted_from` 三列；ORM 查询实测报 `no such column: exams.source_name`。即：**考试中心、真题库、真题详情、报告历史四个接口在 dev 库上当前一律 500**。§13 与主计划 §6.23 记录的“全绿”只成立于 pytest 的临时库。
3. **“真题教研数据来源检索”在这份文档里没有方案，是范围外**：§1.3 第 4 条明写「不做真题版权清理与内容采购…本文只定义展示与留痕」（第 41 行）。文档只解决了“来源怎么展示、怎么卡发布”，没有解决“来源从哪来、凭什么能用、谁录谁审、按什么标准结构化”。
4. **现有 3 条真题是“无源真题”**：全部 `is_past_paper=1`、`source='past_paper'`，`source_name` 覆盖率 0，卷内题目全部引用自主题库 `question_id`，其中 g1 数学、g3 数学“期末真题”总分均为 58 分 / 24 题，不可能是原卷。这与 `release/content-compliance/license-ledger.md` 第 12 行「不含真题原卷；如后续引入真题须单独取得授权并登记」直接冲突，也使 L24「每张已发布真题均有 `source_name`」在实际数据上不成立。

**一句话**：文档把“考试中心怎么用、真题怎么展示”设计清楚了；把“真题数据从哪来、能不能用”留成了空白，而运行层还有两个必须先修的硬缺陷。

---

## 一·二、第二轮复核（2026-11-14 15:30 之后，对应 D-09 v1.1 / CR-005 实施后）

> 本节为**最新结论**，覆盖 §1 的即时判断；§2~§8 保留第一轮原文作为历史记录，状态以本节附表为准。

### R2.0 复核基线（与第一轮相比发生了什么）

| 事实 | 第一轮（15:29 前） | 第二轮（本次） | 证据 |
|---|---|---|---|
| D-09 版本 | v1.0「已生效 · 已实施」 | **v1.1「已生效 · 待更新」**，新增 CR-005、§14、§15 | 文档 mtime 15:58:29；第 5~6 行 |
| Alembic 版本 | `current = a2b3c4d5e6f7`，落后 head 一个 | **`current = c5d6e7f8g9h0`（head）**，五列齐备 | `alembic current/heads` 均返回 `c5d6e7f8g9h0` |
| ORM 可用性 | `no such column: exams.source_name` | **查询成功**（`select(Exam).limit(3)` 返回 3 行） | ORM 探针 |
| 审核发布流 | 文档 Q3 = 「不做」 | **已实施四态状态机**（`draft/pending_review/published/offline`）+ 审核队列 + 审计 | `exams.py:579-742`；迁移 `c5d6e7f8g9h0_exam_review.py` |
| 真题数据 | 3 卷，`source_name` 0 覆盖 | **4 卷全部 `is_past_paper=1`**，`source_name` 4/4 有值 | DB 实测 |
| 测试 | 文档声明 432 例 | 文档声明 440 例；**本轮实跑审核子集 14 passed** | `pytest -q tests/test_exam_review.py tests/test_backfill_exam_sources.py tests/test_exam_center.py` |

### R2.1 已关闭项

| 编号 | 结论 | 复核证据 |
|---|---|---|
| **P0-1（迁移未落库）** | **已关闭**。`alembic current = c5d6e7f8g9h0 = head`；`exams` 表现含 `source_name/license_note/adapted_from/reviewed_by/reviewed_at/published_by/published_at/review_note` 共 8 列；ORM 查询成功，四接口不再因缺列 500 | `alembic current/heads`、`PRAGMA table_info(exams)`、ORM 探针 |
| **P1-3（CORS 未暴露 `X-Total-Count`）** | **未关闭**（第一轮 P1 系列整组未动，见 R2-07） | `main.py` 全文 grep `expose_headers` 0 命中 |

### R2.2 新增 / 仍开放问题（按严重度）

| 编号 | 级别 | 问题 | 证据 | 建议 |
|---|---|---|---|---|
| R2-01 | **P0** | **3 张演示卷“字段合规但内容不合规”**：`source_name` 已填「内置演示数据（非真实真题原卷）」，但 `is_past_paper=1`、`status=published`、标题仍为「深圳市…期末真题（2025）」、`reviewed_by/published_by` 均 NULL → 既标称真题、又自称非真题原卷，且**未经任何复核即处于 published**，与 v1.1 §5.7 状态机（真题须 `draft → pending_review → published`）直接冲突 | DB 行 1~3；文档第 287~290 行、第 493 行（§15 承认待裁决 EX-13） | 二选一落定：① `is_past_paper=0` + 标题改「模拟卷（参照…结构）」，彻底退出真题库；② 若坚持真题标记，须补真实 `source_name/license_note` 并按状态机重走复核。**不接受“来源字段写着非真题、产品上仍叫真题”的中间态** |
| R2-02 | **P0** | **一张生成卷被标成真题并自审自发**：id=4「小学数学单元测试卷」，`source='generated'`、`year=NULL`、`region=NULL`、`is_past_paper=1`、`source_name='QA_demo_source_R07_registered'`、`reviewed_by=published_by=1`、`review_note` 空 | DB 行 4；文档第 460 行「EBG 真机…admin 组卷」、第 493 行承认「另有 1 张真机 QA 演示卷」 | 立即撤销其 `is_past_paper`（它是单元卷，不是真题）；QA 演示卷应走独立 demo 库或带 `source_name='QA 演示（不可对外）'` 且 `status=offline`，不得 `published` 进学生可见真题库 |
| R2-03 | **P1** | **“双人复核”没落地**：`approve` 一步同时把 `reviewed_by` 与 `published_by` 写成同一个 `current.id`，与 §5.7 P2「复用 P2-09 双人复核」不符 → 留痕无独立性，等于自审自发 | `exams.py:717-720` | 拆成“复核人 approve → 发布人 publish”两步，或 approve 时校验 `reviewed_by` 与执行发布者不同；至少禁止同一账号连续 review+publish |
| R2-04 | **P1** | **下线不可逆**：状态机只有 `published → offline`，无 `offline → draft/published` 回归路径，误下线只能人工改库 | `exams.py:697-701`、`725-726` | 增加 `offline → draft`（带审计），或提供“重新上架”动作并要求重新复核 |
| R2-05 | P1 | **上一轮 P1 系列未修**：① `status/window_state` 仍是取数后内存过滤；② `X-Total-Count = len(result)` 取的是截断集；③ 真题库 `page=None` 仍 `limit(60)` | `exams.py:404`、`480`、`844`、`922`；`main.py` 无 `expose_headers` | 按第一轮 P1-1/P1-3/P1-2 执行；先做 SQL 下推与总数口径，再补 CORS |
| R2-06 | P1 | **运行库 0 张普通卷**：4 卷全为真题，学生 `GET /api/exams` 必为空 → L21/L22 的“筛选与状态矩阵”在真实数据上无法演示验收 | DB 实测 `count(*)=4, sum(is_past_paper=1)=4` | 补 1~2 张普通卷（各状态、各窗口）作为验收样本；或明确“dev 库仅演示真题，考试中心验收改用测试库” |
| R2-07 | P2 | `reject` 意见可空（`if payload.note:` 才落 `review_note`）→ 退回无理由；审核队列 `limit(200)` 固定无分页 | `exams.py:727-728`、`:628` | reject 强制 note（422 `EXAM_REVIEW_NOTE_REQUIRED`）；队列分页 |
| R2-08 | P2 | `_reviewable_or_404` 只校验 `is_past_paper`，未校验 `class_id` → 带班级的真题也能进审核队列 | `exams.py:586-593` | 加 `class_id is None` 校验（真题不该带班级） |
| R2-09 | 立项 | **真题来源检索规范仍缺**（第一轮 §6.2 八要素一字未动）；文档第 6 行自述整改计划 CR-006「待 PM 评审，评审通过前不可作为开发依据」 | 文档第 6 行、§15 | CR-006 评审通过后按八要素成文；在此之前不启动真题采集 |

### R2.3 对 D-09 v1.1 §14 / §15 的对账意见

| # | 文档表述 | 核对结果 | 建议 |
|---|---|---|---|
| 1 | §14「缺来源真题 0 张」 | 字面成立（4/4 有 `source_name`），但其中 3 张的来源值是「非真实真题原卷」、1 张是 QA 串 → **“有来源字段”≠“有真实来源”** | 改为分两栏统计：「有 `source_name` 4/4；其中可对外真题 0/4」，避免用字段覆盖率替代内容真实性 |
| 2 | §14「EBG 真机完成…admin 组卷全链路」 | 与 DB 中 id=4 的 QA 卷对应，但该卷被写成 `is_past_paper=1` 且 `published` | 真机验收证据应写“演示卷”，并在库内标 `source_name='QA 演示（不可对外）'`+`offline`，否则验收留下了污染数据 |
| 3 | §15 已登记 P0-1（已解决）/ P0-2（部分处置） | **对账准确**，方向正确；但漏了 id=4 污染卷，以及“`reviewed_by` 为空即视为未审核”的判据 | 补 R2-01/R2-02 两条进 §15；把判据写成“真题 `published` ⇒ `reviewed_by/published_by/reviewed_at/published_at` 非空” |
| 4 | 头部「已生效 · 待更新」+ CR-006 待评审 | 自洽，且比 v1.0 的「已实施」更诚实 | 保留；建议在 §14 标题加限定「仅代码与单测层面完成，运行库数据整改见 EX-13」 |

### R2.4 第二轮结论与优先级

**结论**：**设计层面仍通过（v1.1 的审核流设计合理）；实现层面从“不可用”改善为“可用但有数据污染”；合规层面仍未闭环**。

执行顺序（与第一轮 §7 合并后的最新版）：

| 序 | 事项 | 级别 | 归属 | 前置 |
|---|---|---|---|---|
| 1 | 3 张演示卷落定方案 ①/②（退出真题库或补真实来源并重走复核） | P0 | EX-13 / 需 PM 裁决 | 无 |
| 2 | 撤销 id=4「小学数学单元测试卷」的 `is_past_paper`，QA 演示卷改 `offline` | P0 | EX-13 | 无 |
| 3 | 审核流补“复核人与发布人不同”约束 + `reject` 必填意见 + `offline→draft` 回归 | P1 | 代码小改（可并入 EX-09 收口） | 无 |
| 4 | 筛选 SQL 下推、`X-Total-Count` 口径、CORS `expose_headers`、真题库默认分页 | P1 | 第一轮 P1-1~P1-4 | 无 |
| 5 | 补普通卷样本，恢复考试中心可验收 | P1 | 数据 | 1、2 完成 |
| 6 | 《真题来源检索与录入规范》按 §6.2 八要素成文 | 立项 | CR-006 评审通过后 | PM 评审 |

### R2.5 第二轮复验清单（可直接执行）

```powershell
$Be = 'D:\ai\prj\trae\HuaWei\AiLearning\backend'
$Py = "$Be\.venv\Scripts\python.exe"

# 1) 迁移与列
Push-Location $Be; & $Py -m alembic current; Pop-Location
& $Py -c "import sqlite3;c=sqlite3.connect(r'$Be\ailearning_dev.db');print(len([r for r in c.execute('PRAGMA table_info(exams)')]))"

# 2) 真题来源与审核留痕（期望：真题 published 的 reviewed_by 全部非空）
& $Py -c "import sqlite3;c=sqlite3.connect(r'$Be\ailearning_dev.db');print(c.execute(\"select count(*),sum(case when source_name is null then 1 else 0 end),sum(case when reviewed_by is null then 1 else 0 end) from exams where is_past_paper=1 and status='published'\").fetchone())"

# 3) 普通卷数量（期望 ≥1，否则考试中心不可验收）
& $Py -c "import sqlite3;c=sqlite3.connect(r'$Be\ailearning_dev.db');print(c.execute('select count(*) from exams where is_past_paper=0').fetchone())"

# 4) 审核流回归
Push-Location $Be; & $Py -m pytest -q tests/test_exam_review.py tests/test_backfill_exam_sources.py; Pop-Location
```

通过判据：① `alembic current` 为 head；② 真题 `published` 且 `reviewed_by` 为空的条数为 0；③ 普通卷 ≥1；④ 审核流测试全绿；⑤ ORM 探针无缺列错误。

---

## 二、分项评分

| 维度 | 评级 | 依据 |
|---|---|---|
| 考试中心页面设计（§4） | ★★★★☆ | 状态矩阵唯一决策、六态覆盖、错误码映射、空态区分、权限到元素；缺 `grading` 中间态与重试上限 |
| 接口与模型变更（§6/§7） | ★★★★ | 参数全可选、响应体保持数组、单迁移脚本、错误码齐、静态路径前置；分页/筛选的实际实现与表述有偏差（见 P1-1） |
| 真题来源与版权**展示**（§5.5/§5.7） | ★★★☆ | 四字段 + 缺来源 422 + 卡片/详情展示 + 禁用违规表述，设计到位 |
| 真题数据来源**检索与获取** | ★ | 明确排除在范围外（第 41 行），全库无渠道、授权、录入、覆盖、去重要素 |
| 声明与实现一致性（§13 / 主计划 §6.23） | ★★ | 迁移未落库、真题 0 来源、存量补录未做却标 `DONE` |
| 兼容与回归（L26） | ★★★★ | 可选参数策略与错误码设计良好；`status/window_state` 内存过滤削弱了“兼容且正确” |

---

## 三、设计层面确认通过（无需返工）

| # | 项 | 结论 |
|---|---|---|
| 1 | 口径单一（所有筛选只做 §8.7.1 谓词之后的 AND 收窄） | 通过。§8.1 契约不变声明清楚，代码 `exams.py:390-393` 亦如此实现 |
| 2 | 状态 × 窗口矩阵（§4.4） | 通过。六行唯一决策，`scheduled/closed` 禁用并给文案，无 attempt 不静默（L19 延续） |
| 3 | 真题三条硬边界（§5.1） | 通过。不进通用列表与 `pending_exams`、`published + class_id is None` 才展示，代码 `exams.py:650-654` 一致 |
| 4 | 溯源字段与发布卡口（§5.5 / §5.7 P1） | 通过（设计）。`source_name/license_note/adapted_from` 三字段 + `EXAM_SOURCE_REQUIRED` 422（`exams.py:1774`） |
| 5 | 文档漂移处置（D-1 ~ D-4） | 通过。D-2 取“改文档”最小改动、D-3 保留防御分支并注明不可达、D-4 只补教师视图语义，均未破坏已验收行为 |
| 6 | 分级与任务拆分（EX-04~EX-08） | 通过。P1 22 h / P2 10 h，依赖关系清楚，与 L21~L26 一一映射 |

---

## 四、P0 缺陷（必须立即处理）

### P0-1｜溯源迁移未落到 dev 库，四个考试接口当前不可用

**证据链**

| 证据 | 内容 |
|---|---|
| `backend/alembic/versions/b4c5d6e7f8g9_exam_provenance.py:20-21` | `revision = "b4c5d6e7f8g9"`，`down_revision = "a2b3c4d5e6f7"` |
| `alembic heads` | 输出 `b4c5d6e7f8g9 (head)` |
| `alembic current`（backend 目录） | 输出 `a2b3c4d5e6f7` → **恰好落后一个版本** |
| `PRAGMA table_info(exams)` | 列清单无 `source_name / license_note / adapted_from` |
| `backend/app/models/exam.py:75-77` | 三列已映射为 `Mapped[Optional[str]]` |
| ORM 探针（直连 dev 库 `select(Exam).limit(3)`） | `OperationalError (sqlite3.OperationalError) no such column: exams.source_name` |

**影响**：`GET /api/exams`、`GET /api/exams/past-papers`、`GET /api/exams/past-papers/{id}`、`GET /api/exams/attempts` 因 ORM 会 SELECT 全部映射列而全部抛异常 → 考试中心与真题库页面在 dev 环境打开即报错。§13 与主计划 §6.23 的“pytest 432 全绿”不足以证明运行库可用，因为测试库是走迁移链新建的。

**附带风险**：`backend/app/db/session.py` 默认 engine 为 `sqlite:///./ailearning_dev.db`（相对当前工作目录）。本次探测在非 backend 目录首跑时出现 `no such table: exams`，说明一旦启动目录不同就会连到一个新建空库。建议把库路径解析为基于 `__file__` 的绝对路径或由 `settings` 显式提供。

**建议动作**（不改代码，仅运维）
1. 在 `backend` 目录执行 `alembic upgrade head`（应先备份 `ailearning_dev.db`）。
2. 升级后立即冒烟：`/api/exams`、`/api/exams/past-papers`、`/past-papers/filters`、`/attempts` 各调一次，确认 200。
3. 按 §1.7 DoD 补“空库升级 + 存量库升级”两次记录（本次属存量库升级）。
4. 库路径改为确定性路径，避免 CWD 依赖。

### P0-2｜现有 3 条“真题”是无源真题，与 R-07 台账冲突、使 L24 不成立

**实测数据**

| id | 标题 | 年级/学科 | year | region | 题量 | 总分 | `source_name` |
|---|---|---|---|---|---|---|---|
| 1 | 深圳市一年级数学期末真题（2025） | g1 / math | 2025 | 深圳 | 24 | 58 | 空 |
| 2 | 深圳市一年级语文期末真题（2025） | g1 / chinese | 2025 | 深圳 | 19 | 100 | 空 |
| 3 | 深圳市三年级数学期末真题（2024） | g3 / math | 2024 | 深圳 | 24 | 58 | 空 |

- 三条均 `source='past_paper'`、`status='published'`、`class_id=None`、`window_start/window_end=None`（即 `unscheduled`，动作矩阵会按“开始模考”呈现）。
- 卷内 `questions` 引用 `question_id` = 1/14/20…（卷1）、25/31/47…（卷2）、157/179…（卷3），全部落在自主题库（现 11678 题）范围内 → **不是原卷，是自主题抽题拼卷**。
- g1 数学与 g3 数学均 58 分 / 24 题（10×3 + 10×2 + 4×2），结构雷同，进一步印证由同一组卷模板生成。
- `release/content-compliance/license-ledger.md:12`「示例题目…不含真题原卷；如后续引入真题须单独取得授权并登记」→ 台账未登记、来源为空，与“真题”标注冲突。
- D-09 §5.5 第 4 条（第 270 行）要求「未补齐 `source_name` 的真题不得 `published`」；§13（第 437 行）把“存量真题 `source_name` 按 R-07 台账补录”列为未完成。两者叠加 → **L24 在真实数据上不成立**。

**建议动作**（二选一，均为数据口径操作，不涉及代码）
- **方案 ①（推荐，成本最低、不造假）**：三卷改标为“模拟卷（参照 2025/2024 深圳期末结构）”，置 `is_past_paper=0`、标题去掉“真题”，作为结构示范卷保留。
- **方案 ②**：若确有原卷依据，按 R-07 台账登记 `source_name`（发布机构 + 卷名）、`license_note`（授权凭证编号）、录入人、审核人、审核时间后，保留 `is_past_paper=1`。
- 无论哪个方案，都应在同一批次更新台账 §1 的“示例题目”行，写明真题/模拟卷的当前状态。

---

## 五、P1 / P2 实现缺陷（不阻断设计，影响筛选正确性）

| 编号 | 级别 | 问题 | 证据 | 建议 |
|---|---|---|---|---|
| P1-1 | P1 | `status` / `window_state` 是“取数后内存过滤”，不是 SQL 下推：先按 `hard_limit` 截断，再在 Python 里 `continue`，且 `X-Total-Count` 取的是**过滤后截断集**的长度 | `exams.py:400-401`（`hard_limit=100/1000`）、`:432-436`（内存过滤）、`:476`（`X-Total-Count = len(result)`） | category 判定改为 SQL（`EXISTS(attempt)` 子查询）或先 `count()` 后分页；否则“已完成”筛选会漏卷、总数失真，与 §4.3「服务端筛选」表述不符，L21 的“筛选完整”不成立 |
| P1-2 | P1 | 真题库 `page=None` 时仍 `limit(60)`，超过 60 条的年份/地区仍会被截断 | `exams.py:669` | §5.3 说的“老卷翻不到”只是被 `page` 参数缓解、未根除；建议默认 `page=1&page_size=20`，或先取 `count` 再取数 |
| P1-3 | P1 | CORS 未暴露 `X-Total-Count`，浏览器/Flutter Web 端读不到分页总数 | `backend/app/main.py:54-58`（只有 `allow_origins/allow_methods/allow_headers`） | 增加 `expose_headers=["X-Total-Count"]` |
| P1-4 | P1 | `attempt_status`（真题库）同为内存过滤；`GET /attempts` 固定 `limit(200)` | 真题库过滤段；`exams.py:552` | 同 P1-1 下推或显式分页 |
| P2-1 | P2 | D-2 裁决为“改文档”，后端仍仅 `get_current_user`；`grade` 参数对非学生开放且无角色校验；非学生视图不排除真题（D-4 只补文档） | `exams.py:643`、`:655-658`；§2.3 D-2/D-4 | 给 `grade` 参数加角色校验；在 D-03 §10.5 写清“教师/管理员视图可见全部含真题” |
| P2-2 | P2 | “无 attempt → SnackBar 报告尚未生成”未定义 `grading` 中间态与重试上限 | §4.4；`exams.py:426-431` | 卡片增加“批改中”态与预计等待文案，避免用户反复点击 |
| P2-3 | P2 | 列表响应把 `license_note` 下发给学生端 | `exams.py:471` | 学生视图可只给 `source_name`，`license_note` 留在详情页/管理侧 |

---

## 六、“真题教研数据来源检索方案”缺口与补齐骨架

### 6.1 为什么是缺口

| 文档表述 | 位置 | 含义 |
|---|---|---|
| 「不做真题版权清理与内容采购；真题来源与授权按 D-08 §合规红线、D-01 §真题版权要求执行，本文只定义**展示与留痕**」 | 第 41 行 | 来源获取与授权不在本方案范围 |
| 「存量真题回填由内容教研按 R-07 台账补录，不猜测来源」 | 第 337 行 | 只有原则，无操作规范 |
| 「存量真题 `source_name` 按 R-07 台账补录」列为未实施 | 第 437 行 | 至今未做 |

现状可核：`docs/` 全目录、`backend/app`、`release/content-compliance/license-ledger.md` 中均无“真题采集渠道 / 授权路径 / 结构化录入 / 覆盖目标 / 去重规则”的成文规范；`license-ledger.md` 只登记了自编题、教材版本、图标字体，真题栏为空。

### 6.2 建议补齐的 8 个要素（可直接作为《真题来源检索与录入规范》的章节骨架）

1. **来源分层与准入白名单**：① 官方公开卷（教育局 / 考试院 / 学校官网公开发布）② 学校授权卷（书面授权）③ 出版授权卷（教辅真题汇编，需授权书）④ 改编自编卷（**禁止标注为“真题”**）。逐类写清“需要的凭证”与“允许的对外表述”。
2. **检索渠道与合规边界**：只取公开发布渠道；必录 `来源 URL + 发布机构 + 发布日期 + 采集日期`；明令禁止爬取付费题库、教辅电子版、付费公众号内容。
3. **版权判定三步**：是否已公开 → 是否属事实性题目（可合理使用） → 是否必须取得授权；对应给出 `license_note` 的三种标准写法模板（含凭证编号位）。
4. **结构化录入规范**：原卷 → `Exam(year/region/exam_type/source_name/总分/时限/题量/window)`；题目必须真实落入 `questions` 并置 `source_type=external|adapted`、初始 `status=draft`；**禁止用自主题库抽题冒充原卷**（当前 3 卷即此错）。
5. **与现有 11678 题库的挂接与去重**：题干归一化（可复用 `content-templates/_find_same_content.py` 的剥离册次前缀法）后比对；命中则复用并写 `adapted_from`，未命中新建；给阈值（例如同卷题干与库内重合率 ≥30% 判“非原卷”，不予真题标记）。
6. **录入—复核—发布留痕**：Q3 已把审核流推后，但至少需离线台账（录入人 / 审核人 / 审核时间 / 凭证编号），否则 L24 的“可追溯”只有展示、没有证据链。
7. **覆盖目标与缺口报表**：先做深圳 g1–g9 语数英，2023–2025 每年每科 ≥1 卷；用已实现的 `GET /api/exams/past-papers/filters` 驱动“年份 × 地区 × 学科 × 年级”缺口矩阵，按缺口排采集优先级。
8. **验收指标**：`source_name` 覆盖率 100%；0 卷自造冒充；总分 / 时限 / 题量与原卷一致；自编解析须标 `adapted_from` 或“解析为自编”；违规表述（官方 / 押题 / 名师）扫描 0 命中。

---

## 七、整改清单（按执行顺序）

| 序 | 编号 | 优先级 | 动作 | 是否需授权/改代码 | 验收方式 |
|---|---|---|---|---|---|
| 1 | P0-1 | P0 | 备份 dev 库 → `alembic upgrade head` → 四个接口冒烟 | 需授权（改库） | `alembic current` 显示 `b4c5d6e7f8g9`；接口 200 |
| 2 | P0-2 | P0 | 3 卷改标“模拟卷”（方案 ①）或补来源与台账（方案 ②）+ 同步 `license-ledger.md` §1 | 需授权（改数据口径/台账） | 真题库无“无源真题”；L24 可复验为真 |
| 3 | P1-1 | P1 | `status/window_state` 下推 SQL + `X-Total-Count` 口径修正 | 改代码 | 造 1000+ 卷压测，筛选结果与总数一致 |
| 4 | P1-3 | P1 | CORS 加 `expose_headers` | 改代码 | 浏览器端可读到 `X-Total-Count` |
| 5 | P1-2 / P1-4 | P1 | 默认分页化、`attempt_status` 下推、`/attempts` 分页 | 改代码 | 跨过 60 / 200 上限仍可翻到历史数据 |
| 6 | P2-1 ~ P2-3 | P2 | 角色校验、`grading` 态文案、`license_note` 不下发学生 | 改代码/文档 | 单测 + 真机走查 |
| 7 | §6.2 | 立项 | 《真题来源检索与录入规范》按 8 要素成文，再启动真题采集 | 文档 | 8 个要素齐全，可执行 |
| 8 | QA | 待补 | EBG 真机补跑考试中心筛选 / 真题年份筛选 / 来源详情页 | — | 真机截图 |

**排序理由**：P0-1 是“页面直接打不开”，必须先修；P0-2 是合规红线（对外写“真题”却无来源），与代码无关、成本最低；P1 系列影响筛选正确性与分页可信度，放在采集新真题之前修掉，避免“数据一多就错”；规范立项最后做，但不阻塞 P0/P1。

---

## 八、复验方法（供下轮评审直接跑）

```powershell
$Be = 'D:\ai\prj\trae\HuaWei\AiLearning\backend'
$Py = "$Be\.venv\Scripts\python.exe"

# 1) 迁移版本（应为 b4c5d6e7f8g9）
Push-Location $Be; & $Py -m alembic current; & $Py -m alembic heads; Pop-Location

# 2) 三列是否已存在
& $Py -c "import sqlite3;c=sqlite3.connect(r'$Be\ailearning_dev.db');print([r[1] for r in c.execute('PRAGMA table_info(exams)')])"

# 3) 真题来源覆盖率（期望 100%）
& $Py -c "import sqlite3;c=sqlite3.connect(r'$Be\ailearning_dev.db');print(c.execute(\"select count(*), sum(case when source_name is null or trim(source_name)='' then 1 else 0 end) from exams where is_past_paper=1\").fetchone())"

# 4) ORM 探针（应无 no such column）
& $Py "$env:TEMP\orm_probe2.py"
```

复验通过判据：① `alembic current = b4c5d6e7f8g9`；② `exams` 含三列；③ 真题 `source_name` 缺失数为 0（或真题数为 0）；④ ORM 探针输出“查询成功”；⑤ 四个接口 200 且 `X-Total-Count` 与筛选结果一致。

---

## 九、整改实施结果（2026-11-14 起，按评审意见执行；含第二批收口）

PM 授权「按你的意见执行」后按 §七 顺序落地，实施范围＝数据口径整改 + 代码加固，**未做**：真题采集、真实来源补录、EBG 真机走查。

### 9.1 数据口径（P0-2 / 方案 ①：退出真题库）

备份：`backend\build\backups\ailearning-backup-20261114-161126-pre-exam-fix.db`（9.8 MB）。改库脚本 `%TEMP%\fix_demo_papers.py`（前后快照 + 校验，事务提交）。

| id | 改前 | 改后 | 处置依据 |
|---|---|---|---|
| 1 | 深圳市一年级数学期末**真题**（2025）· `past_paper` · `published` · `is_past_paper=1` | 同标题改「**模拟卷**」· `source=mock` · `is_past_paper=0` · `review_note` 留痕 | R2-01：卷内题为自主题库拼装，非真实原卷 |
| 2 | 深圳市一年级语文期末**真题**（2025） | 同上 | 同上 |
| 3 | 深圳市三年级数学期末**真题**（2024） | 同上 | 同上 |
| 4 | 小学数学单元测试卷 · `generated` · `published` · `is_past_paper=1` · `source_name=QA_demo_source_R07_registered` | `status=offline` · `is_past_paper=0` · `source_name=QA 演示（不可对外）` | R2-02：QA 真机组卷演示数据，不得对外 |

改后校验：真题（`is_past_paper=1`）**0** 张；普通卷 **4** 张；`published ∧ is_past_paper ∧ reviewed_by is null` = **0**；标题含“真题” = **空集**。

同步 `backend\scripts\seed.py`：三条演示种子标题改「期末模拟卷」、创建参数 `source="mock"` / `is_past_paper=False`、幂等查询去掉 `is_past_paper=True` 条件——重跑 seed 不会复活“真题”，且能命中已有行不重复插入。`py_compile` 通过。

### 9.2 代码加固（P1 系列 + 审核流补强）

| 文件 | 改动 | 对应条目 |
|---|---|---|
| `app/schemas/exam.py` | `ExamReviewIn.decision` 扩为 `approve/reject/offline/restore`，docstring 写明双人复核与退回必填 | R2-03 / R2-04 / R2-05 |
| `app/api/routes/exams.py` | 新增 `_last_submitter_id()`：查本卷最近一条 `exam.review.submit` 审计（`detail.contains("exam={id},")`，逗号避免 `exam=5` 命中 `exam=50`） | R2-03 |
| 同上 | `approve`：提交人＝复核人 → 409 `EXAM_REVIEW_SELF` | R2-03 |
| 同上 | `reject`：`note` 空白 → 422 `EXAM_REVIEW_NOTE_REQUIRED`；同时清空 `published_by/published_at` | R2-04 |
| 同上 | 新增 `restore`：`offline → draft`，清空 `reviewed_by/reviewed_at/published_by/published_at`，强制重走提交复核 | R2-05 |
| 同上 | `list_exams`：`status_filter` 改 `exists()` 子查询、`window_state` 改 `and_/or_` 时间谓词，**先过滤再取数**；`X-Total-Count = select(count()).select_from(stmt.subquery())`；分页 `offset/limit` 下推 | R2-06 |
| 同上 | `list_past_papers`：`attempt_status` 同样下推 SQL；`limit(60)` 仅作用于分页后；总数改过滤后真实值 | R2-06 |
| `app/main.py` | CORS 增 `expose_headers=["X-Total-Count"]` | R2-06（浏览器可读分页头） |
| `app/lib/features/exam/exam_review_page.dart` | 退回前弹必填意见框（空意见本地拦截）、`offline` 卷新增「回草稿重审」按钮、决策文案补 `restore` | 前端适配（后端新增决策/错误码不打断闭环） |
| `app/lib/core/errors/api_error_guide.dart` | 新增 `EXAM_REVIEW_SELF` / `EXAM_REVIEW_NOTE_REQUIRED` / `EXAM_INVALID_STATE` 中文引导 | 同上 |
| `tests/test_exam_review.py` | 原首例补「另一账号提交」审计；新增自审阻断 + 退回无意见、restore 回草稿两例 | R2-03/04/05 验收 |
| `tests/test_exam_center.py` | 新增 101 卷用例：仅最早一张有进行中记录，旧实现被 `limit(100)` 截断丢卷，新实现能查到且 `X-Total-Count=1` | R2-06 回归 |

### 9.3 验证结果

| 项 | 命令 | 结果 |
|---|---|---|
| 后端全量 | `python -m pytest -q` | **446 passed / exit 0**（第二批收口后复跑） |
| 审核流子集 | `python -m pytest -q tests/test_exam_review.py` | **8 passed** |
| 考试中心子集 | `python -m pytest -q tests/test_exam_center.py tests/test_exam_review.py` | **16 passed** |
| 前端全量 | `flutter test` | **175 passed** |
| 前端静态检查 | `flutter analyze`（改动两文件） | No issues found |
| 语法 | `py_compile`（seed / exams / schemas / main） | 通过 |
| ruff | `ruff check` 改动文件 | 项目非门禁（全仓基线 1186 条既有告警，本次未引入新类型；测试内 `%` 格式化已改 f-string） |

### 9.4 文档同步

- `docs\exam-center-and-past-papers-design.md` §5.7 已补：`restore` 流转、双人复核 409 `EXAM_REVIEW_SELF`、退回必填 422 `EXAM_REVIEW_NOTE_REQUIRED`、演示数据口径（模拟卷/`source=mock`）、列表筛选下推与 `X-Total-Count` 口径、CORS `expose_headers`。

### 9.5 原未闭环 5 条 · 收口状态（2026-11-14 第二批）

| # | 原未闭环项 | 处置 | 状态 |
|---|---|---|---|
| 1 | `/api/exams/attempts`、`/api/exams/reviews` 固定 `limit(200)` 未分页 | 两接口加 `response: Response` + `page/page_size`，`X-Total-Count` 取过滤后 `count()`，`offset/limit` 下推；无 `page` 时保留 200 条兼容上限（旧客户端行为不变） | **已完成** |
| 2 | `_reviewable_or_404` 未校验 `class_id` | 增 `class_id is not None` → 409 `EXAM_CLASS_COPY_NOT_REVIEWABLE`（"班级派发的真题副本不进入审核队列，请操作其模板卷"） | **已完成** |
| 3 | `license_note` 随列表/详情下发学生端 | 新增 `_license_note_for(exam, viewer)`：`role == "student"` 返回 `None`；`_detail_out` / `_attempt_out` 增 `viewer` 形参，4 处调用点全部传入当前用户；管理侧（审核队列、generate 响应）保留原文 | **已完成** |
| 4 | 真题来源检索与录入规范未成文；真题库空 | 成文 `docs/past-paper-source-intake-spec.md`（九章、八要素齐：来源分层 L1~L4 与禁止自主题拼装 / 检索渠道白名单黑名单 / 版权三步 + 3 类 `license_note` 模板 / 卷级题级结构化录入 / 去重阈值重合率 ≥30% / 离线台账 11 列 / 深圳 g1–g9 语数英 2023–2025 覆盖目标 / 8 项验收指标 / 与代码文档对应表）；真题库仍为**空库**（0 张），属已确认的预期状态，不作缺陷 | **已完成（规范）/ 预期（空库）** |
| 5 | 主计划验收状态未回写；EBG 真机走查未做 | 主计划已回写：§1.1 D-09「已更新 v1.1」、§3.12 转正式任务并标实施结果（含新增 EX-18）、§4.1 I-013/I-014 `RESOLVED`、I-015 `MITIGATED`、§5.5 Changelog v2.02、§6.25 转「已通过并实施」、新增 **§6.26 验收记录**（含真机走查清单）。EBG 真机：本机无 Android 设备接入（同 I-005），**未执行**，清单已落 §6.26.3 | **部分完成**：文档回写已完成；真机走查待设备接入 |

### 9.6 复验命令（可复查）

```powershell
# 数据口径
& $env:TEMPerify_exams.py                       # 期望：真题 0 / 普通 4 / published 真题缺来源 0

# 后端
Push-Location D:\ai\prj\trae\HuaWei\AiLearning\backend
& .venv\Scripts\python.exe -m pytest -q          # 期望：446 passed / exit 0
& .venv\Scripts\python.exe -m pytest -q tests/test_exam_center.py tests/test_exam_review.py   # 期望：16 passed
Pop-Location

# 前端
Push-Location D:\ai\prj\trae\HuaWei\AiLearning\app
flutter test        # 期望：175 passed
flutter analyze     # 期望：改动文件 No issues
Pop-Location

# 回退数据库（必要时）
Copy-Item -Force "D:\ai\prj\trae\HuaWei\AiLearning\backend\build\backups\ailearning-backup-20261114-161126-pre-exam-fix.db" "D:\ai\prj\trae\HuaWei\AiLearning\backend\ailearning_dev.db"
```

### 9.7 本轮遗留（不属 D-09 五条范围）

| 项 | 说明 | 建议 |
|---|---|---|
| EX-12 库路径绝对化 | `Settings.database_url` 默认 `sqlite:///./ailearning_dev.db` 仍依赖 CWD | 纳入下一批：改基于项目根的绝对默认路径 + 不同启动目录用例 |
| `grade` 参数角色校验 | 学生传 `grade` 仍可跨年级窥视列表口径 | 纳入 EX-17 剩余项，D-03 §10.5 写清视图口径 |
| 卡片 `grading` 中间态与重试上限 | 前端已有 `pendingReport`，无重试上限 | 纳入 EX-17 |
| R-07 台账真题栏 | 规范已定义 11 列字段，台账无真题条目 | 与首次真实采集同批登记 |

---

## 附录 A：证据行号汇总

| 类型 | 位置 | 要点 |
|---|---|---|
| D-09 | §1.3 第 4 条（第 41 行） | 明示不做真题版权清理与内容采购，只定义展示与留痕 |
| D-09 | §5.5 第 4 条（第 270 行） | 未补 `source_name` 不得 `published` |
| D-09 | §7.1（第 337 行） | 存量回填由教研按 R-07 台账补录，不猜来源 |
| D-09 | §13（第 437 行） | “存量真题 `source_name` 按 R-07 台账补录”列为未实施 |
| D-09 | §4.3（第 149-155 行） | 声明筛选在服务端执行 |
| D-09 | §5.3（第 248 行） | 年份必须下推服务端，否则 `limit(60)` 截断 |
| 迁移 | `backend/alembic/versions/b4c5d6e7f8g9_exam_provenance.py:20-30` | `revision/down_revision` 与三个 `add_column` |
| 模型 | `backend/app/models/exam.py:75-77` | 三列 ORM 映射 |
| 路由 | `backend/app/api/routes/exams.py:400-401,432-436,476` | `hard_limit` + 内存过滤 + 总数口径 |
| 路由 | `backend/app/api/routes/exams.py:669` | 真题库 `limit(60)` |
| 路由 | `backend/app/api/routes/exams.py:552` | `/attempts` 固定 `limit(200)` |
| 路由 | `backend/app/api/routes/exams.py:1774` | `EXAM_SOURCE_REQUIRED` |
| 路由 | `backend/app/api/routes/exams.py:511,536,574` | 三个新接口注册位置（静态路径在 `/{exam_id}` 前） |
| 中间件 | `backend/app/main.py:54-58` | CORS 未配 `expose_headers` |
| 台账 | `release/content-compliance/license-ledger.md:12` | 「不含真题原卷；引入须单独取得授权并登记」 |
| 实测 | `backend/ailearning_dev.db` | `exams` 3 行，全部 `is_past_paper=1`，`source_name` 0 覆盖，题 id 指向自主题库 |
| 实测 | ORM 探针 | `no such column: exams.source_name` |
| 实测 | `alembic current` / `heads` | `a2b3c4d5e6f7` vs `b4c5d6e7f8g9` |

---

## 附录 B：本次评审未做的事项（明确边界）

- 未执行 `alembic upgrade head`、未修改 3 卷真题数据、未改 `license-ledger.md`、未改任何代码与设计文档。
- 未启动后端做真实 HTTP 冒烟（以 ORM 探针替代，结论等价：映射列缺失必致查询失败）。
- 未评估前端页面细节（`past_paper_page.dart` / `exam_list_page.dart` 的渲染与交互），本轮范围限于文档与后端/数据一致性；前端真机走查仍在 QA 待补项内。
