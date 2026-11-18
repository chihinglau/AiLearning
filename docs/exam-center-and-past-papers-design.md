# 深爱学（AiLearning）考试中心与真题库功能设计方案

> **文档编号**：D-09（新增专项设计方案）
> **文档性质**：已生效专项设计方案（PM 评审通过）
> **版本**：v1.2（CR-006 评审整改落地；2026-11-14）
> **状态**：**已生效 · 待更新**（CR-004：EX-04~EX-08 / L21~L26；CR-005：EX-09~EX-11 / L27~L30，见 §14 与主计划 §6.24）。2026-11-14 评审报告《`docs/exam-center-and-past-papers-review-20261114.md`》结论为「设计通过 / 实现一致性不通过 / 真题来源检索方案缺失」；整改计划见主计划 §3.12 / §6.25（CR-006 **待 PM 评审**，评审通过前不可作为开发依据）。页面级设计与 §8.7.1 口径契约仍有效。
> **日期**：2026-11-14
> **关联 CR**：CR-004（决策「通过」）、CR-005（决策「通过」，覆盖 §12 Q3 原决议；均见主计划 §4.2）
> **编写依据**：`docs/project-task-plan.md` v1.97 §1.1 / §1.2 矩阵维护规则 / §1.7 DoD / §7 第 6 条「先更新设计文档或登记 CR，再改代码」；`docs/learning-page-design.md` v1.2 §3.1、§8.1~§8.7、§12.4、§14.2
> **关联文档**：[learning-page-design.md](./learning-page-design.md)（D-04）、[k12-learning-app-design.md](./k12-learning-app-design.md)（D-01）、[user-role-permission-design.md](./user-role-permission-design.md)（D-03）、[release-plan.md](./release-plan.md)（D-08）、[project-task-plan.md](./project-task-plan.md)
> **范围声明（v1.0 修订）**：本文件先按 PM 要求以 v0.1 草稿交付并待评审，评审通过后作为正式设计依据，已按 §12「通过后动作」完成 EX-04~EX-08 实施（见 §13）。§1~§8 保留评审通过的方案原文，其中 D-04 §8.7.1 口径契约不变；§9/§10 的编号已回填主计划。本文件与主计划 v1.99、D-04 v1.3 配套阅读。

---

## 一、编写依据与问题定义

### 1.1 为什么需要这份方案

CR-003 / EX-01~EX-03 已完成「考试入口闭环与考试入库」（D-04 §8.7、主计划 §6.22，L18~L20 全部 `DONE`）：统一了学生可见性谓词、首页待办考试独立卡、真题库入口、组卷发布与班级派发。但该闭环只覆盖**入口与入库**，两个承载页面本身从未有过完整设计：

| 页面 | D-04 现有描述 | 判定 |
|---|---|---|
| 考试中心 `/exams` | §3.1 三行（可参加 / 进行中 / 已完成）、§9.1 一行接口、§12.4 一行 API | 无页面级方案 |
| 真题库 `/past-papers` | §3.1 一行「v1.2 提升为首页入口」、§8.7.1 一句口径、§12.4 一行 API | 无页面级方案 |

同时，代码中已实现了相当多的细节（双维度筛选、窗口拦截、卡片字段、报告跳转、年份 Chip、刷新/空态/错误重试等），这些功能**从未写入任何设计文档**，属于「代码有 · 设计未写」。若不补齐，后续迭代会出现「以代码反推设计」「口径再次漂移」「验收无依据」三类风险（I-011 即为前车之鉴）。

### 1.2 本次要补齐的三类缺口

| 类别 | 考试中心 | 真题库 |
|---|---|---|
| **[设计缺]** 文档没写、代码已有 | 筛选维度与优先级、状态 × 窗口矩阵、卡片字段、跳转规则、加载/空态/异常、权限到元素 | 独立入口定位、筛选维度、卡片字段、窗口拦截、空态/异常、权限到元素 |
| **[都缺]** 文档与代码都没有 | 服务端筛选、分页、搜索、时间窗筛选器、学科/年级/地区筛选、报告历史回看、多次 attempt 策略 | 年级/地区/类型/状态筛选 UI、年份下推服务端、按年份分组、是否已考与报告回看、来源/版权展示、内容审核发布流 |
| **[漂移]** 文档与代码不一致 | D-04 §12.4 写 `/self-grade`，代码为 `/self-assess`；D-03 §10.5 写列表接口需 `learn:exam:take`，后端实为 `Depends(get_current_user)` | `pending_exams.entry=past_paper` 在统一谓词下不可达（防御性死分支）；非学生角色 `GET /api/exams` 未排除真题 |

### 1.3 非目标与红线

1. **不改变 D-04 §8.7.1 已生效的口径契约**：真题仍不进通用考试列表、不进 `pending_exams`；`student_visible_exam_clauses()` 仍是唯一学生可见性谓词。
2. 不改答题页 `/exam/:id`、报告页 `/exam/report/:attemptId` 的内部逻辑（计时、防抖、离线队列、自评、雷达图等），本文只定义「如何到达它们」。
3. 不引入强防作弊、不引入第三方 SDK、不改现有 `Exam.status` 语义。
4. 不做真题版权清理与内容采购；真题来源与授权按 D-08 §合规红线、D-01 §真题版权要求执行，本文只定义**展示与留痕**。
5. 本方案评审通过前，不得据此改代码（§7 第 6 条）；评审通过后须先回填主计划 §1.2 / §3.10 / §6.1 三处编号，再按 §1.5 状态流转 `TODO → DOING → DONE`。

---

## 二、现状基线（评审事实核对）

### 2.1 已生效的设计约定（不得推翻）

| 约定 | 来源 |
|---|---|
| `pending_exams` 与 `GET /api/exams`（学生）共用 `student_visible_exam_clauses()`，排除 `is_past_paper=true`、`source='assignment'`、非本班班级卷、非 `published`、非本年级、已交卷、`closed` | D-04 §8.7.1；`recommendation.py` |
| 真题仅由 `GET /api/exams/past-papers` 与首页「真题库」承载 | D-04 §8.7.1 / §12.4 |
| 首页待办卡按 `entry` 直达 `/exam/:id` 或 `/past-papers`，最多 3 条，窗口状态给提示 | D-04 §8.7.2 |
| 组卷入库与班级派发走 `POST /api/exams/generate`、`POST /api/exams/mock`，权限 `content:exam:write` / `learn:assignment:create` | D-04 §8.7.3 |
| 考试类型 `unit/midterm/final/mock/custom`、蓝图与组卷规则、生命周期状态图、报告区块 | D-04 §8.1~§8.5 |

### 2.2 代码已实现、建议本次「追认」为基线（不代表需要重新开发）

| 页面 | 已实现事实 |
|---|---|
| 考试中心 | 状态筛选 `all/available/in_progress/completed` + 类型筛选 `all/unit/midterm/final/mock`（均为客户端本地过滤）；下拉刷新、加载/错误重试、空态；卡片展示标题、状态、类型、学科、学年、题量、满分、限时、窗口区间、得分/剩余/待批改；`windowOpen` 拦截；已完成按 `attempt.id` 跳报告；无 `attempt` 给 SnackBar |
| 真题库 | 独立接口 `GET /api/exams/past-papers?subject=&year=&region=`；学科 Chip（全部/语文/数学/英语）；年份 Chip 从已加载结果本地提取并本地过滤；刷新/加载/错误重试/空态；卡片展示标题、学科、年份、地区、题量、满分、限时、开放时间；「开始模考」按钮带窗口拦截 |
| 后端 | `student_visible_exam_clauses()` 5 条件；`_window_state()` 四态 `unscheduled/scheduled/open/closed`；`_ensure_takeable()` 校验年级/窗口/班级；`GET /api/exams` 的 `type/status` Query 与 `limit(100)`；`GET /api/exams/past-papers` 的 `limit(60)`、`year desc,id desc` 排序、学生按 `current.grade` 隐式过滤；11 个考试路由 |
| 模型 | `Exam` 含 `year/source/exam_type/window_start/window_end/region/is_past_paper/class_id/status`；`ExamSummary` 含 `window_state/attempt/is_past_paper/region` |

> 评审动作：确认以上为「现有基线」，本方案在其上做**增量设计**，不把它当成待开发项重复排期。

### 2.3 需评审一并裁决的文档漂移

| # | 漂移 | 建议处置 |
|---|---|---|
| D-1 | D-04 §12.4 写 `POST /api/exams/attempts/{id}/self-grade`，代码为 `/self-assess` | 评审通过后修订 D-04 §12.4（不改代码） |
| D-2 | D-03 §10.5 写 `GET /api/exams`、`/api/exams/past-papers` 需 `learn:exam:take`，后端仅 `get_current_user`，权限由前端 `PermissionGate` 守卫 | 二选一：① 文档改为「登录 + 前端路由守卫」；② 后端补 `require_permission`（属实施项）。**建议 ①**，避免破坏现有调用 |
| D-3 | `build_pending_exams()` 保留 `entry=past_paper` 分支，但统一谓词已排除真题，分支不可达 | 建议保留为防御分支并在代码/文档注明「当前不可达」；若将来放开真题待办，必须同步改谓词并新增验收项 |
| D-4 | 非学生角色调用 `GET /api/exams` 不排除 `is_past_paper` | 明确「教师/管理员视图」语义后再定；若要求一致，则把谓词的「真题排除」提取为公共条件 |

---

## 三、总体设计与信息架构

### 3.1 页面地图（补充 D-04 §3.1，评审通过后合并）

```
学习 Tab
├── 学习首页 /learn
│   ├── 「待办考试」独立卡（D-04 §8.7.2，已生效）
│   └── 「考试入口」三卡：考试中心 / 真题库 / 班级作业（已生效）
├── 考试中心 /exams                        ← 本方案 §4
│   ├── 筛选栏：状态 / 类型 / 学科 / 时间窗 / 搜索（P1 分级见 §3.3）
│   ├── 分组列表：进行中 → 可参加 → 已完成（默认排序）
│   ├── 卡片：字段见 §4.5；动作见 §4.4
│   ├── 报告历史 /exams/history（P2，新增路由）
│   └── 空态 / 加载 / 错误重试
├── 真题库 /past-papers                    ← 本方案 §5
│   ├── 筛选栏：年份 / 学科 / 年级 / 地区 / 类型 / 状态（P1 分级见 §3.3）
│   ├── 按年份分组的试卷列表（默认 `year desc`）
│   ├── 卡片：字段见 §5.4；来源/版权标识见 §5.5
│   ├── 真题详情/预览 /past-papers/:id（P2，新增路由）
│   └── 空态 / 加载 / 错误重试
├── 考试管理与发布 /exams/manage（已生效，D-04 §8.7.3）
├── 考试答题 /exam/:examId（已生效）
└── 考试报告 /exam/report/:attemptId（已生效）
```

> 新增路由 `/exams/history`、`/past-papers/:id` 属 **P2 建议**，评审未通过前不注册。路由顺序约束沿用 CR-003 经验：静态路径（`/exams/history`、`/api/exams/blueprints`）必须注册在动态段 `/{exam_id}` 之前。

### 3.2 设计原则

1. **口径单一**：筛选只能收窄，不得放宽 §8.7.1 的可见性谓词；服务端过滤为准，客户端筛选退化为展示辅助。
2. **兼容优先**：现有接口新增参数一律可选，未传时行为与今天完全一致；列表响应体保持数组，分页总数走响应头，避免破坏现有客户端。
3. **权限最小**：学生只看本人年级/本班范围；`content:exam:write` 只影响管理入口与写接口；`learn:exam:report:self` 只放行本人报告。
4. **状态可解释**：卡片上的每个按钮都由「窗口状态 × 作答状态」唯一决定，禁止静默点击（延续 L19）。
5. **真题可追溯**：任何对外展示的真题都必须能回答「哪一年、哪个地区、来源于哪、授权状态如何」。
6. **分级交付**：P1 为本期必需（口径、筛选下推、状态闭环、来源展示），P2 为增强（搜索、分页、报告历史、详情页、日历视图），避免一次性膨胀。

### 3.3 分级

| 级别 | 考试中心 | 真题库 |
|---|---|---|
| **P1（建议本期）** | 筛选下推服务端、状态/窗口矩阵、卡片与跳转规则、空态异常、无 attempt 提示、权限映射、文档漂移修订 | 年份下推服务端、学科/年级/地区筛选、是否已考与报告回看、来源/版权展示、入库字段、空态异常、权限映射 |
| **P2（可选/后续）** | 搜索、分页、时间窗筛选器/日历、报告历史页、多次 attempt 回看、按考试聚合错题、排序偏好持久化、埋点 | 搜索、分页、真题详情/预览、按年份分组折叠、类型/状态筛选、跨年级浏览、内容审核发布流、排序偏好 |

---

## 四、考试中心页（`/exams`）方案

### 4.1 页面目标

让学生在单一页面回答三个问题：**有哪些我能参加的考试 → 该点哪一个 → 考完去哪看结果**。默认进入按「进行中 → 可参加 → 已完成」分组，进行中优先置顶（延续断点续答价值）。

### 4.2 数据契约（列表项字段）

| 字段 | 来源 | 说明 | 变更 |
|---|---|---|---|
| `id` / `title` / `subject` / `grade` / `exam_type` | `ExamSummaryOut` | 基础标识与类型标签 | 现有 |
| `total_score` / `time_limit_min` / `question_count` | `ExamSummaryOut` | 卡片副信息 | 现有 |
| `window_start` / `window_end` / `window_state` | `ExamSummaryOut` | 四态 `unscheduled/scheduled/open/closed` | 现有 |
| `category` | `GET /api/exams` 按最新 attempt 计算 | `available/in_progress/completed` | 现有 |
| `attempt` | `GET /api/exams` | 最新一次 attempt 的 `id/status/grading/remaining/total_score` | 现有 |
| `region` / `year` / `is_past_paper` / `class_id` | `ExamSummaryOut` | 卡片来源/范围标识；**学生视图下 `is_past_paper` 恒为 false** | 现有 |
| `source_name` / `license_note` | 建议新增（仅真题/外部卷） | 溯源展示，见 §7 | **建议 P2** |
| `attempt_count` | 建议新增 | 是否展示「查看历史报告」入口的依据 | **建议 P2** |

### 4.3 筛选、排序与分页

| 维度 | 取值 | 执行位置 | 级别 |
|---|---|---|---|
| 状态 | `all/available/in_progress/completed` | **服务端**（`status` Query 已存在，前端当前未使用） | P1 |
| 类型 | `all/unit/midterm/final/mock/custom` | **服务端**（`type` Query 已存在，前端当前未使用） | P1 |
| 学科 | `all/chinese/math/english/...`（按年级开课科目动态取，禁止硬编码三科） | 服务端 `subject` | P1 |
| 时间窗 | `all/open/scheduled/closed` | 服务端 `window_state` | P2 |
| 搜索 | 标题模糊匹配 | 服务端 `q` | P2 |
| 分页 | `page` / `page_size`（默认 20，上限 100） | 服务端；总数走 `X-Total-Count` 响应头，**响应体仍为数组** | P2 |
| 排序 | 默认「进行中 → 窗口开始时间升序 → 创建时间降序」；可选 `window_start`/`created_at` | 服务端 `sort` | P2 |

**P1 硬性要求**：把现有两组本地筛选改为调用 `examService.list(type:, status:, subject:)`，使「筛选结果」与「首页待办口径」同源；筛选后为空与全量为空必须区分文案（「没有符合条件的考试」/「暂无考试，去练习」）。

### 4.4 状态矩阵与跳转规则（唯一决策表）

| 窗口状态 | 作答状态 | 卡片主按钮 | 点击行为 |
|---|---|---|---|
| `open` | 无 attempt | 开始考试 | `POST /api/exams/{id}/attempts` → `/exam/:examId` |
| `open` | 进行中 | 继续答题 | `/exam/:examId`（断点续答） |
| `open` | 已交卷/批改中 | 查看报告 | 有 `attempt.id` → `/exam/report/:attemptId`；无 → **SnackBar「报告尚未生成，请稍后重试」**（禁止静默，L19） |
| `scheduled` | 任意 | 未开始（禁用） | SnackBar「开放时间：<window_start>」 |
| `closed` | 任意 | 已结束（禁用） | SnackBar「考试窗口已结束」；已交卷者仍可进报告 |
| `unscheduled` | 无 attempt | 开始考试 | 视同 `open`，展示「不限时窗口」 |

错误码沿用 `_ensure_takeable()`：年级不符 `EXAM_GRADE_MISMATCH`、非本班 `EXAM_NOT_MEMBER`、窗口未开/已关 `EXAM_WINDOW_*`，前端统一映射为可读提示，不裸露英文码。

### 4.5 卡片信息架构

- 第一行：标题 + 状态徽标（进行中/可参加/已完成/已结束）。
- 第二行：类型 · 学科 · 学年 · 地区（有值时）。
- 第三行：题量 / 满分 / 限时 / 窗口区间（`windowLabel`）。
- 第四行（按状态）：进行中显示剩余时间与已答数；已完成显示得分或「待批改」；可参加显示「未开始」。
- 底部：主按钮（§4.4）+ 次按钮（P2：查看详情 / 历史报告）。
- 视觉遵循 D-01 §3.6.4 的 `AccentCard` 淡彩底，状态色仅用于徽标，不以颜色单独传达状态（无障碍）。

### 4.6 加载、空态与异常

| 场景 | 表现 |
|---|---|
| 首次加载 | 骨架屏 3 条，不显示「暂无考试」 |
| 下拉刷新 | 保留当前筛选条件，失败回滚原列表并给 SnackBar |
| 网络错误 | 整页错误态 + 「重试」按钮（沿用现有实现） |
| 全量为空 | 空态卡「暂无可参加的考试」+ 去练习入口 |
| 筛选后为空 | 「没有符合条件的考试」+ 「清除筛选」按钮 |
| 权限不足 | 由 `PermissionGate` 拦截路由，页内不重复判权 |
| 数据异常（如 `attempt` 缺失） | 不崩溃、不静默，按 §4.4 给提示 |

### 4.7 报告回看与多次 attempt（P2 建议）

现状：列表只保留每卷最新一次 attempt，报告按 `attemptId` 单实例查看。建议新增 `GET /api/exams/attempts?exam_id=&page=` 与 `/exams/history` 页，按考试聚合历次成绩（时间、得分、用时、报告入口），并在报告页顶部提供「本次/历次」切换。**不改变现有 `GET /api/exams/attempts/{id}/report` 契约**。

### 4.8 权限映射

| 元素 | 权限/约束 |
|---|---|
| 页面路由 `/exams` | `learn:exam:take`（前端 `PermissionGate`，现状） |
| 列表数据 | 学生：§8.7.1 谓词；教师/管理员：按 D-03 §6 数据范围（口径待裁决，见 §8.2） |
| 报告按钮 | `learn:exam:report:self`，且 `attempt.user_id == current.id` |
| 「考试管理与发布」入口 | `content:exam:write`（不在本页，仅「我的」页） |

### 4.9 性能与埋点（P2）

- 沿用 L14：`GET /api/exams` P95 < 300 ms（本地库）；分页后单页 ≤ 20 条。
- 埋点建议：`exam_center_view` / `exam_center_filter`（维度：status/type/subject）/ `exam_card_click`（维度：category/window_state）。埋点不得采集题干与学生答案。

---

## 五、真题库页（`/past-papers`）方案

### 5.1 定位与边界

真题库是**独立的历年真题浏览与模考入口**，不复用通用考试列表。三条硬边界：

1. 真题（`is_past_paper=true`）不进 `GET /api/exams`（学生）、不进 `pending_exams`；首页待办卡不因真题计数。
2. 首页「真题库」卡与待办卡 `entry=past_paper` 是**列表级入口**，不承诺直达某张卷；`entry=past_paper` 当前为防御性死分支（§2.3 D-3）。
3. 真题库只允许 `status=published`、`class_id is None` 的卷；班级派发卷、作业卷、草稿一律不出现。

### 5.2 数据契约

| 字段 | 来源 | 说明 | 变更 |
|---|---|---|---|
| `id` / `title` / `subject` / `grade` / `year` / `region` | `PastPaperOut` | 基础标识；`year` 用于分组，`region` 用于筛选 | 现有 |
| `exam_type` / `total_score` / `time_limit_min` / `question_count` | `PastPaperOut` | 卡片副信息 | 现有 |
| `window_start` / `window_end` / `window_state` | 建议补齐 | 现状 `PastPaperOut` 未含，前端靠 `ExamSummary` 默认值回退；应显式下发 | **建议 P1** |
| `source` | `Exam.source` | 现有值域含 `mock/generated/mock_class/assignment` | 现有 |
| `source_name` / `license_note` / `adapted_from` | 建议新增 | 真题溯源与授权留痕，见 §5.5 / §7 | **建议 P1** |
| `attempt` | 建议新增 | 是否已考、进行中、报告 ID，支撑 §5.4 动作 | **建议 P1** |
| `is_reviewed` | 建议新增 | 内容审核状态，支撑 §5.7 | **建议 P2** |

### 5.3 筛选、分组与排序

| 维度 | 取值 | 执行位置 | 级别 |
|---|---|---|---|
| 年份 | `all/2026/2025/...`（由服务端返回可用年份列表，不再从已加载项客户端提取） | 服务端 `year`（已存在，前端未传） | **P1** |
| 学科 | 按年级开课科目动态取，取消硬编码三科 | 服务端 `subject` | **P1** |
| 年级 | 默认 `current.grade`；是否允许跨年级浏览由 PM 裁决（§11 Q4） | 服务端 `grade` | **P1** |
| 地区 | `all/深圳/广东/全国/...` | 服务端 `region`（已存在，前端无 UI） | **P1** |
| 类型 | 中考/高考/一模/二模/期末真题等（需定义枚举） | 服务端 `exam_type` | P2 |
| 状态 | `all/未考/进行中/已考` | 服务端 `attempt_status` | P2 |
| 搜索 / 分页 | `q` / `page` / `page_size`，总数走 `X-Total-Count` | 服务端 | P2 |
| 分组排序 | 默认按 `year desc` 分组，组内 `region → subject → id`；年份可折叠 | 客户端渲染（数据已按序） | P1 |

**P1 硬性要求**：年份筛选必须从「客户端过滤已加载的 60 条」改为服务端参数，否则 `limit(60)` 会截断历史年份，出现「老卷永远翻不到」的隐性缺陷。

### 5.4 卡片与动作

| 状态 | 主按钮 | 行为 |
|---|---|---|
| 未考 + `open`/`unscheduled` | 开始模考 | `POST /api/exams/{id}/attempts` → `/exam/:examId` |
| 进行中 | 继续模考 | `/exam/:examId` |
| 已考（有报告） | 查看报告 | `/exam/report/:attemptId` |
| 已考（批改中） | 待批改（禁用） | SnackBar「报告生成中，请稍后重试」 |
| `scheduled` | 未开放（禁用） | 显示开放时间 |
| `closed` | 已结束（禁用） | 已考者仍可看报告 |

卡片字段：年份徽标 + 地区 + 标题 + 学科/年级 + 题量/满分/限时 + 开放时间 + 来源标识（§5.5）。**禁止**在卡片上写「真题原卷」以外的暗示性表述（如「官方」「押题」），遵循 D-08 §内容合规与 R-07 违规表述扫描结论。

### 5.5 真题来源与版权展示（P1 强制）

D-01 §真题版权要求「公开真题注明来源」、D-08 §合规红线要求「题源台账（来源/授权凭证/录入人/审核人）」。方案要求：

1. 每张真题卡片展示来源摘要：`来源：{source_name} · {year} · {region}`，无 `source_name` 时显示「来源待补录」而非空白。
2. 详情页（P2）展示完整溯源：`source_name` / `license_note` / `adapted_from` / 录入人 / 审核人 / 审核时间。
3. 真题内容不得直接搬运教辅出版物解析；改编题须在 `adapted_from` 标明，遵循 R-07 题源与授权台账。
4. 未补齐 `source_name` 的真题不得对外发布（`status=published`）——由 §5.7 入库流程卡口保证。

### 5.6 空态与异常

| 场景 | 表现 |
|---|---|
| 本年级无真题 | 「当前年级暂未收录真题」+ 返回考试中心 |
| 筛选后为空 | 「没有符合条件的真题」+ 清除筛选 |
| 跨年级被禁 | 不展示年级切换控件，并在页脚说明「仅展示当前年级真题」 |
| 网络错误 / 加载 | 与 §4.6 一致（错误重试 / 骨架屏） |
| 来源字段缺失 | 卡片显示「来源待补录」，不阻断浏览；管理侧告警 |

### 5.7 内容入库与审核流（v1.1 已实施）

CR-004 阶段（v1.0）只落地 P1 最小方案：真题溯源字段 + 来源必填 `EXAM_SOURCE_REQUIRED`，`POST /api/exams/generate` 生成即 `status=published`。**CR-005 按 PM 追加要求采纳 P2 完整方案**（覆盖 §12 Q3 原决议），实施口径如下：

- **仅真题走草稿**：`is_past_paper=true` 生成即 `status=draft`；普通卷仍生成即 `published`，CR-003 / L20「生成后立即进入学生可见列表」行为不变，`student_visible_exam_clauses()` 与 §8.7.1 契约不变。
- **状态机**：`draft → pending_review → published`；`pending_review → draft`（退回）；`published → offline`（下线）；`offline → draft`（**restore** 误下线纠正，回草稿后须重新提交复核，不直接复原 `published`）。非法流转返回 409 `EXAM_INVALID_STATE`。
- **双人复核**（评审 R2-03，2026-11-14 实施）：`approve` 时取本卷最近一条 `exam.review.submit` 审计的提交人，若与当前复核人相同则拒绝，返回 409 `EXAM_REVIEW_SELF`；提交与发布必须由不同账号完成。
- **退回留痕**（评审 R2-04）：`reject` 必须携带 `note`（空白视为未填），缺失返回 422 `EXAM_REVIEW_NOTE_REQUIRED`；`reject` 时清空 `published_by / published_at`，回到 `draft` 重走提交。
- **卡口**：`submit-review` 与 `approve` 均校验真题 `source_name` 非空，缺来源返回 422 `EXAM_SOURCE_REQUIRED`；真题库只查 `published`，草稿 / 待复核 / 下线 / 无来源卷一律不对外可见。
- **留痕**：`Exam` 增 `reviewed_by / reviewed_at / published_by / published_at / review_note`，审核动作写审计 `exam.review.*`，复用 `content:review:decide`（P2-09 双人复核资产）。
- **存量卷**：不得猜测来源，按 R-07《题源与授权台账》显式补录；未补录的 `published` 真题由补录脚本隔离为 `draft`（EX-11 / L29）。
- **演示数据口径**（评审 R2-01 / R2-02，2026-11-14 实施）：seed 生成的三套内置演示卷为**模拟卷**（`is_past_paper=false`、`source="mock"`、标题为「期末模拟卷」），不进真题库、不需审核；QA 演示卷 `id4` 已撤销真题标记并置 `offline`。真题库只接受有 R-07 台账来源的真实卷。
- **列表口径**（评审 R2-06）：`GET /api/exams` 与 `GET /api/exams/past-papers` 的 `status / attempt_status / window_state` 全部下推为 SQL 条件后再取数与分页，`X-Total-Count` 为**过滤后、分页前**的真实总数；`main.py` CORS 增 `expose_headers=["X-Total-Count"]`，浏览器端可读。
- **队列分页**（评审 §9.5-1，2026-11-14 实施）：`GET /api/exams/attempts`（作答历史）与 `GET /api/exams/reviews`（审核队列）均接受 `page / page_size`（上限 100，默认 20），返回 `X-Total-Count` 为过滤后总数；**不带 `page` 时保留原 200 条上限**，旧客户端行为不变。
- **审核队列准入**（评审 §9.5-2）：`_reviewable_or_404` 除 `is_past_paper` 外增加 `class_id is None` 校验——班级派发的真题副本返回 409 `EXAM_CLASS_COPY_NOT_REVIEWABLE`（提示「请操作其模板卷」），副本不进复核流、不改模板卷状态。
- **授权说明可见性**（评审 §9.5-3）：`license_note` 只在管理侧下发（审核队列、组卷结果、教师/管理员视图）；`role == "student"` 时考试详情、作答历史、考试中心与真题库列表一律返回 `null`，学生端只保留 `source_label` 来源标签。实现为 `_license_note_for(exam, viewer)`，`_detail_out` / `_attempt_out` 均显式传 `viewer`。
- **采集规范**（评审 §6.2 / CT-04）：真题来源的检索边界、版权判定、结构化录入、去重阈值、台账字段与覆盖目标见 `docs/past-paper-source-intake-spec.md`（D-10，v1.0）；真题库为**空库**属预期状态，首次采集前不得以演示卷充抵。

> 该流程与 R-07 台账对齐；实现见 §14、验收见主计划 §6.24（L27~L30）。

### 5.8 权限映射

| 元素 | 权限/约束 |
|---|---|
| 路由 `/past-papers` | `learn:exam:take`（现状） |
| 列表数据 | `status=published`、`is_past_paper=true`、`class_id is None`、年级范围（§5.3） |
| 开始模考 / 报告 | 同 §4.8 |
| 真题入库与审核 | `content:exam:write` / `content:review:decide` |

---

## 六、接口变更建议（评审通过后实施）

### 6.1 现有接口扩展（全部为可选参数，默认行为不变）

| 接口 | 建议新增参数 | 说明 |
|---|---|---|
| `GET /api/exams` | `subject`、`window_state`、`q`、`page`、`page_size`、`sort` | 已有 `type`、`status`；分页时返回 `X-Total-Count`，**响应体保持数组** |
| `GET /api/exams/past-papers` | `grade`、`exam_type`、`attempt_status`、`q`、`page`、`page_size` | 已有 `subject`、`year`、`region`；响应补 `window_state`/`attempt`/来源字段 |
| `POST /api/exams/generate` | `year`、`region`、`source_name`、`license_note`、`adapted_from` | 仅 `is_past_paper=true` 时校验来源必填 |
| `GET /api/exams/blueprints` | — | 不变（CR-003 已验收） |

### 6.2 建议新增接口

| 接口 | 用途 | 级别 |
|---|---|---|
| `GET /api/exams/attempts?exam_id=&page=` | 报告历史 / 多次 attempt 回看 | P2 |
| `GET /api/exams/past-papers/{id}` | 真题详情与溯源展示（不含答案） | P2 |
| `GET /api/exams/past-papers/filters` | 下发可用年份/地区/学科枚举，避免前端硬编码 | P1 |

### 6.3 兼容性与错误码

- 所有新增参数可空；不传时接口行为、排序、条数上限与今天一致（避免回归 CR-003 的 L18）。
- 新增错误码：`EXAM_SOURCE_REQUIRED`（422，真题缺来源）、`EXAM_FILTER_INVALID`（422，枚举外取值）。
- 沿用既有 `EXAM_NOT_SUBMITTED`（409）、`EXAM_NOT_MEMBER`（403）、`EXAM_GRADE_MISMATCH`、`EXAM_WINDOW_*`。
- 静态路径注册顺序：`/exams/past-papers/filters`、`/exams/attempts`、`/exams/blueprints` 必须在 `/exams/{exam_id}` 之前（CR-003 经验）。

---

## 七、数据模型变更建议

### 7.1 P1 最小方案（推荐）

`Exam` 新增 3 个可空字段：`source_name VARCHAR(200)`、`license_note TEXT`、`adapted_from VARCHAR(200)`；`PastPaperOut` 补 `window_state`/`attempt`/`is_reviewed`（其中 `is_reviewed` 可由 `status` 推导则不落库）。

- 需 1 个 Alembic 迁移；按 §1.7 DoD 第 6 条，**空库升级与存量库升级各验证一次 + `seed` 幂等**。
- 存量真题回填由内容教研按 R-07 台账补录，不猜测来源。

### 7.2 P2 完整方案（CR-005 已实施，v1.1 修订）

不新建独立表，按「优先复用现有内容审核资产」给 `Exam` 加 5 个可空留痕列：`reviewed_by`（Integer）、`reviewed_at`（DateTime）、`published_by`（Integer）、`published_at`（DateTime）、`review_note`（Text）；审核动作写 `record_audit` 的 `exam.review.*`，权限复用 `content:review:decide`。真题 `status` 值域扩为 `draft / pending_review / published / offline`；普通卷值域仍为 `published`，`student_visible_exam_clauses()` 的 `status == "published"` 谓词不变。

新增 1 个 Alembic 迁移（接在 `b4c5d6e7f8g9` 之后），按 §1.7 DoD 第 6 条验证空库升级与存量库升级；迁移只加可空列，不改存量卷状态（存量卷由 EX-11 脚本按 R-07 台账处置）。

### 7.3 明确不做（v1.1 修订）

- 不改 `student_visible_exam_clauses()` 与 §8.7.1 契约，不改普通卷「生成即 `published`」的 L20 行为。
- 不改 `ExamAttempt` / `ExamAnswer` 结构，不做数据库分库分表，不新建 `exam_reviews` 表。
- 不为存量真题猜测来源；不把人工签署 / 人工试听记为技术 `DONE`。

---

## 八、口径一致性（不改变 §8.7.1）

### 8.1 契约不变声明

本方案所有筛选、分组、排序、分页都建立在 §8.7.1 谓词**之后**收窄，任何情况下不得把真题、作业卷、非本班班级卷、草稿、已交卷、关闭窗口的卷放回学生可见列表。新增的服务端参数只做「AND 条件」，不得替换谓词。

### 8.2 三个待裁决的口径问题

| # | 问题 | 选项 |
|---|---|---|
| Q-A | 非学生角色 `GET /api/exams` 是否排除真题？ | ① 明确「教师/管理员视图可见全部」（文档补说明）；② 统一排除（改后端） |
| Q-B | `pending_exams.entry=past_paper` 死分支 | ① 保留为防御分支并注释；② 删除并同步 `exam_entry.dart`；③ 放开真题待办（须改谓词 + 新增验收） |
| Q-C | 真题库年级范围 | ① 严格锁定 `current.grade`（现状）；② 允许学生在年级范围内切换查看（需明确未成年人内容边界） |

---

## 九、验收标准建议（编号 L21~L26，预留，评审通过后回填三处）

> **v1.0 状态**：以上 L21~L26 已由 PM 评审通过后，按 §12 约定在主计划 §6.1 / D-04 §14.2 / D-01 §8.3 **三处同步**登记，状态均为 `DONE`（证据见主计划 §6.23）。编写草稿时全库检索 `L21` 起、`CR-004`、`EX-04` 起、`I-012` 起均 0 命中，无编号冲突；`I-012` 起仍为预留。

| 编号 | 验收项（建议） | 判定 |
|---|---|---|
| L21 | 考试中心筛选与可见性口径一致 | 任一筛选组合的结果集均为 `student_visible_exam_clauses()` 的子集；`type/status/subject` 下推服务端，返回与首页待办不矛盾 |
| L22 | 考试中心状态矩阵完备 | §4.4 六种组合各有唯一按钮与明确反馈；`scheduled/closed` 禁用且给提示；已完成缺 `attempt` 不静默；无跳转变空白页 |
| L23 | 真题库筛选服务端化与分组 | `year/subject/grade/region` 由服务端过滤；跨过 `limit(60)` 的历史年份仍可查到；按 `year desc` 分组且组内有序 |
| L24 | 真题来源与版权可追溯 | 每张已发布真题均有 `source_name`；缺来源无法发布（422）；卡片与详情页展示来源，不出现「官方/押题/名师」违规表述 |
| L25 | 真题库动作闭环 | 未考→开始、进行中→续答、已考→报告、批改中/未开放/已结束→禁用+提示，六态覆盖且真题始终不进通用列表与待办卡 |
| L26 | 兼容与回归 | 不带新参数时接口行为与 CR-003 验收态一致；L18~L20 全部回归通过；新增/变更文件 `pytest` 全绿、`ruff`/`dart analyze` 0 issue、前端新增 ≥1 个模型/状态测试；若有迁移，空库+存量库升降级通过 |

---

## 十、任务拆分建议（EX-04~EX-08，评审通过后登记 §3.10）

> **v1.0 状态**：以上任务已按 §1.2 规则登记为主计划 §3.10 任务组，并逐项 `TODO → DOING → DONE`；§5.1 快照更新为 `DONE 101 / TODO 0`（预估 32 h、实际 24 h，证据见主计划 §3.10 / §6.23）。EX-08 的真题审核发布流按 §11 Q3 裁决列为后续，未计入本轮。

| ID | 任务（建议） | 负责人 | 预估(h) | 优先级 | 依赖 | 验收映射 |
|---|---|---|---|---|---|---|
| EX-04 | 考试中心筛选下推服务端 + 卡片状态矩阵与异常文案；修订文档漂移 D-1/D-2 | AR/FE | 6 | P1 | 无 | L21/L22、L26 |
| EX-05 | 真题库筛选服务端化（年份/学科/年级/地区）、分组排序、可用筛选项接口 | AR/FE | 6 | P1 | EX-04 | L23、L26 |
| EX-06 | 真题溯源字段与迁移、`/exams/manage` 真题表单、来源必填校验、卡片来源展示 | AR/FE/CT | 6 | P1 | EX-05 | L24、L26 |
| EX-07 | 真题库动作闭环（是否已考/进行中/报告回看）+ 权限与空态异常 | FE | 4 | P1 | EX-05 | L25、L26 |
| EX-08 | P2 增强：搜索/分页、报告历史页、真题详情/预览、审核发布流（按 PM 取舍） | AR/FE | 10 | P2 | EX-04~EX-07 | L21~L26 补充项 |

**小计**：P1 22 h + P2 10 h = 32 h（预估，待 PM 排期裁决）。按 §1.5 状态流转，逐项 `TODO → DOING → DONE`，禁止跳步；每项须满足 §1.7 DoD 六项。

---

## 十一、风险与开放问题（PM 裁决清单）

| # | 决策点 | 建议 | 影响 |
|---|---|---|---|
| Q1 | 新增独立 D-09 草稿，还是直接并入 D-04？ | **独立草稿**：D-04 v1.2 已生效，塞入待评审内容会污染基线；评审通过后合并为 D-04 v1.3 或让 D-09 升「待实施」 | 文档结构 |
| Q2 | 分页/搜索/报告历史/详情页是否本期做？ | **列 P2**，P1 只做口径与筛选下推 | 工时 10 h |
| Q3 | 真题是否改为「先草稿→审核→发布」？ | 建议 P2 再做；P1 只补来源必填，避免破坏 L20「生成即入库可见」 | 与 R-07/CR-003 的兼容 |
| Q4 | 真题库是否允许跨年级浏览？ | 建议维持锁定 `current.grade` | 未成年人内容边界 |
| Q5 | `entry=past_paper` 死分支处置 | 建议保留并注释 | §8.2 Q-B |
| Q6 | 非学生视图真题可见性 | 建议文档补说明、不改后端 | §8.2 Q-A |
| Q7 | 文档漂移 D-1/D-2 是否本次一并修订 | 建议一并改文档（不改代码） | D-03/D-04 版本 |
| Q8 | 本方案与 R-A16 / M5 签署的关系 | **不阻塞**：CR-003 验收结论不变，R-A15/R-A16/M5 仍待 PM 签署；QA 补 admin 真机组卷仍独立待办 | 发布节奏 |
| Q9 | 新增 3 个溯源字段触发迁移 | 若 PM 决定不做溯源（Q3 取「否」），P1 可不迁移，改为只展示 `year/region` | 迁移成本 |

---

## 十二、评审记录（PM 已裁决）

| 项目 | 内容 |
|---|---|
| 评审人 | PM（本次会话确认） |
| 评审日期 | 2026-11-14 |
| 评审结论 | ☑ 通过 ☐ 修改后再审 ☐ 驳回 |
| 评审意见 | 「`docs/exam-center-and-past-papers-design.md` 评审通过，立刻按计划执行相关任务」 |
| 决议（Q1~Q9） | Q1 保持 D-09 独立并升 v1.0（D-04 仅同步验收编号与交叉引用，升 v1.3）；Q2 P2 增强本期做搜索/分页接口、报告历史页、真题详情页，审核发布流列后续；Q3 不做「草稿→审核→发布」，维持 L20 行为，仅对真题加来源必填；Q4 维持锁定 `current.grade`；Q5 保留 `entry=past_paper` 防御分支；Q6 仅补文档说明、不改后端；Q7 一并修订 D-1/D-2 漂移；Q8 不阻塞 R-A15/R-A16/M5 签署；Q9 采纳 3 个溯源字段并新增 Alembic 迁移 |
| 通过后动作 | 已完成：① CR-004 决策「通过」+ 决策人；② D-09 升 v1.0 已生效；③ §1.2 矩阵补任务列并转 `DONE`；④ 新增 §3.10 EX-04~EX-08 任务组；⑤ §6.1 / D-04 §14.2 / D-01 §8.3 三处同步 L21~L26；⑥ §5.1 快照、§5.5 v1.99 Changelog、§6.23 验收记录同步；⑦ 按 §7 第 6 条实施并回归 |
| 补充评审（CR-005，2026-11-14） | PM 追加要求「文档登记的后续项要继续制定任务计划并实施」。**Q3 改判**：由「不做草稿→审核→发布」改为采纳 §5.7 P2 完整方案，仅真题生效、普通卷维持 L20；Q2 中「审核发布流列后续」同步解除；Q8 中「QA 补 admin 真机组卷」并入 QA-01；其余 Q1 / Q4~Q9 决议不变。通过后动作：D-09 升 v1.1、新增 §14 实施记录、主计划 §3.11 / §6.24 / L27~L30；人工项（PM 签署、TT-07 试听）按 §1.5 登记 `BLOCKED`，不得代签/代填结论 |

> **当前状态**：已生效 · 已实施。EX-04~EX-08 全部 `DONE`，L21~L26 验收通过（主计划 §6.23）。

---

## 十三、实施记录（EX-04~EX-08，2026-11-14）

| 项 | 结果 |
|---|---|
| 后端接口 | `list_exams` 增 `subject/window_state/q/page/page_size` 与 `X-Total-Count`；`list_past_papers` 增 `grade/exam_type/attempt_status/q/page` 并补 `category/attempt/来源`；新增 `GET /past-papers/filters`、`GET /past-papers/{id}`、`GET /attempts`（静态路径注册在 `/{exam_id}` 前） |
| 数据模型 | `Exam` 增 `source_name/license_note/adapted_from`；新增 `PastPaperFiltersOut`、`ExamAttemptHistoryOut`、`PastPaperDetailOut`；迁移 `b4c5d6e7f8g9_exam_provenance.py` |
| 关键规则 | `generate_exam` 真题缺 `source_name` 在组卷前快速失败 `EXAM_SOURCE_REQUIRED`（422）；学生真题库仍锁定 `current.grade`；所有筛选为 §8.7.1 谓词之后的 AND 收窄 |
| 前端 | 新增 `core/models/exam_action.dart` 六态纯函数、`exam_history_page.dart`、`past_paper_detail_page.dart` 与 `/exams/history`、`/past-papers/:paperId` 路由；`exam_list_page.dart` / `past_paper_page.dart` 改为服务端筛选、分组、来源展示与空态区分；`exam_manage_page.dart` 补 5 个真题溯源输入 |
| 回归 | 全量 `pytest` 432 例（含新增 `test_exam_center.py` 6 例与迁移链用例）、`flutter test` 170 例（含新增 `exam_action_test.dart` 12 例、更新 2 个 widget 测试）全绿；`ruff --select E,F,I` 与 `flutter analyze` 0 issue；`app/pubspec.lock` 无副作用 |
| 文档同步 | 主计划 v1.99（§1.1/§1.2/§3.10/§4.2/§5.1/§5.5/§6.1/§6.23/文末）；D-04 v1.3（§14.2 L21~L26、§12.4 漂移修正）、D-01 §8.3、D-03 §10.5、D-06 §4.3/§9 |
| 后续项处置（v1.1） | §6.23 的 ①~④ 已由 CR-005 / 主计划 §3.11 全部立为受控任务：① EBG 真机补跑 + admin 组卷 → QA-01；② 真题审核发布流 → EX-09 / EX-10（Q3 改判，见 §12 补充评审）；③ 存量真题来源补录 → EX-11；④ PM 签署 → QA-02（`BLOCKED` B-002）。TT-07 人工试听 → QA-03（`BLOCKED` B-001）。实施口径见 §14、验收见主计划 §6.24 |

---

## 十四、后续项收口实施口径（CR-005，2026-11-14）

| 项 | 口径 / 落点 |
|---|---|
| 状态机与权限 | `draft / pending_review / published / offline` 四态；`POST /api/exams/{id}/submit-review`（`content:exam:write`）、`GET /api/exams/reviews` 与 `POST /api/exams/{id}/review`（`content:review:decide`）；静态路径 `/reviews` 注册在 `/{exam_id}` 之前；非法流转 409、缺来源 422 `EXAM_SOURCE_REQUIRED`；动作写审计 `exam.review.*` |
| 可见性契约 | 真题库 / 详情 / 筛选项 / 首页待办一律只看 `status="published"`；草稿、待复核、下线、无来源真题不得进入任何学生可见列表；普通卷仍生成即 `published`，L18~L20 与 §8.7.1 不变 |
| 前端 | 组卷页真题结果卡显示草稿态并提供「提交复核」；新增 `/exams/reviews` 审核队列（通过并发布 / 退回草稿 / 下线），按 `content:review:decide` 显隐；模型与 widget 测试覆盖状态文案与动作调用 |
| 存量来源 | `backend/scripts/backfill_exam_sources.py`：`--report` 出清单、`--apply --source-map` 仅接受 R-07 台账显式映射、`--quarantine` 把未补录的 `published` 真题隔离为 `draft`；**不猜测来源**；seed 的 3 套演示真题补合规标注；R-07 台账新增附节记录 |
| 验收映射 | L27 状态机与权限、L28 前端审核闭环、L29 存量补录与卡口、L30 真机回归与 L18~L26 兼容；执行结果与证据见主计划 §6.24 |
| 人工项 | QA-02（PM 签署 R-A15/R-A16/M5）与 QA-03（TT-07 人工试听）按 §1.5 登记 `BLOCKED`，解除条件见主计划 §4.3 B-002 / B-001 |

**实施结果（2026-11-14）**：新增 Alembic 迁移 `c5d6e7f8g9h0_exam_review.py`（5 个可空留痕列，dev 库由 `a2b3c4d5e6f7` 存量升级通过）；`backend/tests/test_exam_review.py` 4 例、`test_backfill_exam_sources.py` 4 例、`app/test/exam_review_test.dart` 4 例；全量 `pytest` 440 例 / `flutter test` 174 例；新增与改动文件 `ruff --select E,F,I` 0 issue、`flutter analyze` 0 issue；`pubspec.lock` 构建副作用已还原。EBG 真机（SN `2NSDU20423005421`）完成筛选/年份/来源详情/admin 组卷全链路，访问日志见主计划 §6.24。演示卷 3 张已按 R-07 台账标注为内置演示数据，缺来源真题 0 张。

---

## 十五、CR-006 整改落地口径（2026-11-14）

> 评审报告：`docs/exam-center-and-past-papers-review-20261114.md` §九；验收：主计划 §6.26。

| 项 | 落地口径 | 证据 |
|---|---|---|
| 作答历史分页 | `GET /api/exams/attempts` 增 `page/page_size`（默认 1/20，上限 100），`X-Total-Count` = 过滤后总数，`offset/limit` 下推；不带 `page` 保留 200 上限 | `routes/exams.py: list_attempt_history`、`test_attempt_and_review_queues_are_paginated` |
| 审核队列分页 | `GET /api/exams/reviews` 同上；排序仍为 `created_at desc` | 同上 |
| 班级副本隔离 | `_reviewable_or_404`：`class_id is not None` → 409 `EXAM_CLASS_COPY_NOT_REVIEWABLE`；前端错误引导已补 | `test_class_copy_not_reviewable` |
| 授权说明收口 | `_license_note_for(exam, viewer)`：学生 `None`；管理侧保留；`_detail_out` / `_attempt_out` 显式 `viewer` | `test_license_note_hidden_from_students` |
| 审核流补强 | 双人复核 409 `EXAM_REVIEW_SELF`、退回必填 422 `EXAM_REVIEW_NOTE_REQUIRED`、`offline→draft`（`restore`） | `test_exam_review.py` 8 例 |
| 采集规范 | `docs/past-paper-source-intake-spec.md`（D-10，九章、八要素） | 文档评审 |
| 回归 | 后端 `446 passed`、前端 `175 passed`、`flutter analyze` 0 issue | 主计划 §6.26.2 |

**仍待办**：EX-12（`Settings.database_url` 绝对化）、`grade` 参数角色校验与 D-03 §10.5 视图口径、卡片 `grading` 中间态与重试上限、EBG 真机走查（主计划 §6.26.3 清单）、R-07 台账真题栏实填。

---

## 附录 A：现状对照表（供评审核对）

| 对象 | 设计已覆盖 | 代码已有·设计未写 | 都缺（需实施） |
|---|---|---|---|
| 考试中心 | 入口与页面地图三行、§8.1~§8.5 体系、§8.7.1 口径、L18~L20 | 双维度本地筛选与计数、窗口拦截、卡片字段、报告跳转、无 attempt 提示、加载/错误/空态、后端 `category`/`limit(100)`/`_window_state`/`_ensure_takeable` | 服务端筛选、搜索、分页、时间窗筛选器、学科/年级/地区筛选、报告历史、多次 attempt、按考试聚合错题 |
| 真题库 | 入口提升一行、§8.7.1 一句口径、§12.4 一行 API、D-01 §4.5 字段、D-08 版权红线 | 独立接口与 `subject/year/region`、年级隐式过滤、`limit(60)`、3 科 Chip、客户端年份 Chip、刷新/空态/错误、卡片字段、「开始模考」窗口拦截、`is_past_paper` 生成开关 | 年份下推服务端、年级/地区/类型/状态筛选 UI、是否已考与报告回看、分组折叠、搜索/分页、来源/版权展示、内容审核发布流、溯源字段 |

## 附录 B：变更影响面清单（评审通过后）

| 层 | 文件（预计） |
|---|---|
| 后端 | `backend/app/api/routes/exams.py`、`backend/app/schemas/exam.py`、`backend/app/models/exam.py`、`backend/app/services/recommendation.py`（仅口径裁决时）、新增 Alembic 迁移、`backend/tests/` |
| 前端 | `app/lib/features/exam/exam_list_page.dart`、`past_paper_page.dart`、`exam_manage_page.dart`、`app/lib/core/services/exam_service.dart`、`app/lib/core/models/exam.dart`、`app/lib/app.dart`（P2 新路由）、`app/test/` |
| 文档 | D-04（合并或交叉引用）、D-01 §4.6/§8.3、D-03 §10.5、D-06 §4.3 API 清单、D-08（若涉及合规表述）、主计划 §1.1/§1.2/§3.10/§4.2/§5.1/§5.5/§6.1/§6.23/文末 |

> **v1.0 状态**：以上影响面已在 EX-04~EX-08 中按 §13 全部落地；本附录保留为评审时的变更范围核对表。
>
> **v1.2 增量影响面（CR-006 / §15）**：后端 `routes/exams.py`（`_license_note_for`、`_reviewable_or_404` class_id 拦截、`list_attempt_history` / `list_exam_reviews` 分页）、`scripts/seed.py`（模拟卷口径）、`tests/test_exam_center.py`（+3 例）+ `test_exam_review.py`（+3 例）；前端 `exam_review_page.dart`、`api_error_guide.dart`、`app/test/exam_review_test.dart`；数据 `ailearning_dev.db`（4 行口径整改）；文档新增 `docs/past-paper-source-intake-spec.md`、本文件 §5.7/§15、评审报告 §九、主计划 §3.12/§4.1/§5.5/§6.25/§6.26。
>
> **v1.1 增量影响面（CR-005 / §14）**：后端 `routes/exams.py`（新 3 个审核端点 + `generate_exam` 真题草稿）、`schemas/exam.py`（审核请求/响应 + `ExamGenerateOut.status`）、`models/exam.py`（5 个留痕列）、新增 Alembic 迁移、`backend/scripts/backfill_exam_sources.py`、`backend/scripts/seed.py`（演示真题合规标注）、`backend/tests/test_exam_review.py` 与 `test_backfill_exam_sources.py`；前端 `exam_service.dart`、`exam.dart`、`exam_manage_page.dart`、新增 `exam_review_page.dart`、`app.dart`（`/exams/reviews`）、`profile_page.dart`（入口）、`app/test/exam_review_test.dart`；文档 D-01 §4.6/§8.3、D-03 §10.5/§12.2、D-04 §14.2、D-06 §4.3/§9、D-08 §11、R-07 台账 §6 与主计划 §1.1/§1.2/§3.11/§4.2/§4.3/§5.1/§5.5/§6.1/§6.24/文末。

---

## 附录 C：2026-11-14 评审意见与整改结果（CR-006，已通过并实施）

> 2026-11-14 PM 授权「按你的意见执行」后 CR-006 通过（Q1=方案①、Q2=独立成文），整改已落地，口径并入 §5.7 与 §15；本附录保留评审事实与处置结果对照。

| 评审结论 / 缺陷 | 处置 |
|---|---|
| 页面级设计通过（§4.4 状态 × 窗口矩阵、§5.1 真题三条硬边界、§8.1 口径单一、D-1~D-4 漂移处置） | 维持已生效，无需返工 |
| P0-1：dev 库迁移落后一个版本、四接口 500 | **已解决**：CR-005 会话执行 `alembic upgrade head`，当前 `c5d6e7f8g9h0 (head)`，三列存在；遗留「库路径依赖 CWD」列入整改拟立任务 EX-12 |
| P0-2：3 卷无源真题与 R-07 台账冲突 | **已处置（Q1=方案①）**：3 卷标题改「期末模拟卷」、`source=mock`、`is_past_paper=0`，QA 演示卷 `id4` 置 `offline` 并撤真题标记；`seed.py` 同步防复活；改后真题 0 张、标题含「真题」空集 |
| P1-1~P1-4：`status/window_state` 内存过滤、总数失真、`limit(60)/limit(200)`、CORS 未暴露 `X-Total-Count` | 实现偏差仍在，列入 EX-14~EX-16 |
| P2-1~P2-3：角色校验、`grading` 态、`license_note` 下发学生 | 实现偏差仍在，列入 EX-17；D-03 权限口径同步 |
| 真题来源检索与录入规范（评审 §6.2 八要素） | 属本文 §1.3 明列的范围外缺口；是否立项为独立规范文档由 PM 裁决（CT-04） |
| 评审 §6.2 第 6 条「Q3 已把审核流推后」 | **事实校正**：CR-005 已实施真题草稿→复核→发布状态机与 `reviewed_by/published_by` 留痕（§5.7 / §14），该条按现状理解 |

> 整改任务、工时、依赖、验收映射与 PM 待裁决项见 `project-task-plan.md` §3.12 / §6.25。本附录不新增验收编号，L31~L36 在 CR-006 评审通过后登记。
