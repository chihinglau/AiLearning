# 深爱学（AiLearning）项目实施任务计划与进度跟踪

> **文档性质**：项目主计划 / 进度跟踪 / 过程追溯（全程伴随开发周期）
> **版本**：v1.52
> **创建日期**：2026-11-06
> **最后更新**：2026-11-07 02:20（P1-09 主观题自评完成）
> **参考设计文档**：见[§1.1 参考设计文档清单](#11-参考设计文档清单)（共 8 份，含 4 份设计方案、4 份支撑文档）
> **需求追踪**：见[§1.2 需求—设计—任务追踪矩阵](#12-需求设计任务追踪矩阵)
> **维护人**：项目负责人（PM）
> **更新频率**：每次开发会话结束必更；每日一次进度快照；里程碑专项评审

---

## 一、文档使用说明

### 1.1 参考设计文档清单

> 本计划的所有任务、验收标准均来源于下列文档。**需求变更必须先更新对应设计文档或登记 CR（§4.2），再调整本计划任务**，禁止"只改代码不改文档"。

| 编号 | 文档 | 版本 | 类型 | 覆盖范围 | 对应计划任务 | 维护人 | 状态 | 最后核对 |
|---|---|---|---|---|---|---|---|---|
| **D-01** | [k12-learning-app-design.md](./k12-learning-app-design.md) | v0.2 | 总体产品设计 | 产品定位、用户画像、信息架构、里程碑、技术栈 | 基线 B-01~B-05；P0 总体范围 | PM/AR | 已生效（M1/M2 基线） | 2026-11-06 |
| **D-02** | [subject-tutoring-and-m2-design.md](./subject-tutoring-and-m2-design.md) | v1.0 | 学科辅导专项设计 | 五大学法支柱、九学科分学段辅导方案、深圳教材适配、M2 数据模型与算法 | B-03/B-04；P0-17~P0-24；P1-07 | CT/AR | 已生效（M2 已交付） | 2026-11-06 |
| **D-03** | [user-role-permission-design.md](./user-role-permission-design.md) | v1.0 | 角色权限专项设计 | 多级角色体系、年级维度、权限矩阵、数据范围、权限校验、数据模型与 API | P0-01~P0-10；P1-01~P1-06；P2-01/P2-02 | AR/PM | 部分生效（P0 范围已落地，P1/P2 待实施） | 2026-11-06 |
| **D-04** | [learning-page-design.md](./learning-page-design.md) | v1.0 | 学习页专项设计 | 教材绑定、学习首页、知识点分层、智能练习、综合考试、数据流与 API | P0-11~P0-38；P1-07~P1-11；P2-03~P2-07 | FE/AR | 部分生效（P0 范围已落地，P1 待实施） | 2026-11-06 |
| **D-05** | [privacy.md](./privacy.md) | v1.0（2026.11.06） | 合规支撑 | 隐私政策、未成年人数据、家长同意与数据留存 | P0-05/P0-09；P1-05；P2-08 | PM | 源稿（已更新为 K12 版，待公网发布） | 2026-11-06 |
| **D-06** | [skills.md](./skills.md) | 现行 | 工程支撑 | 开发规范、技能与接口使用说明 | 全部任务（开发约定） | AR | 已生效 | 2026-11-06 |
| **D-07** | [skill_github_repo_access.md](./skill_github_repo_access.md) | 现行 | 内部支撑 | 仓库访问与凭据说明（不进入版本库） | 发布/提交相关任务 | AR | 内部参考 | 2026-11-06 |
| **D-08** | [release-plan.md](./release-plan.md) | v1.0 | 发布支撑 | 上架缺口、渠道矩阵、备案/软著、合规红线、素材与时间线 | 发布任务 R-01~R-09；P0-05/P0-09、P1-05、P2-08 | PM/AR | 源稿（待执行） | 2026-11-06 |

**文档优先级**：需求冲突时，`D-01`（总体）> 专项设计（`D-02/D-03/D-04`）> 支撑文档（`D-05`~`D-08`）。专项之间冲突由 PM 裁决并登记 CR。发布相关的合规与上架要求以 `D-08` 为准。

**文档状态说明**：

| 状态 | 含义 |
|---|---|
| 草稿 | 编写中，不可作为开发依据 |
| 待实施（设计已评审） | 设计完成且通过评审，任务可启动 |
| 已生效 | 已落地并有代码/测试证据 |
| 待更新 | 实现与设计出现偏差，需同步修订或登记 CR |
| 废止 | 不再使用，需注明替代文档 |

### 1.2 需求—设计—任务追踪矩阵

> 用于回答三个问题：**这个需求出自哪份文档哪一章？由哪些任务实现？当前到哪一步？**

| 需求域 | 需求来源（文档 §） | 设计方案（文档 §） | 实现任务 | 验收编号 | 当前状态 |
|---|---|---|---|---|---|
| 多级角色体系与权限矩阵 | D-03 §3/§5 | D-03 §3/§5 | P0-03、P1-01、P1-04、P2-01、P2-02 | A8 | `DOING`（常量与鉴权依赖已落地） |
| 学生年级细分与必填 | D-03 §4/§7.1 | D-03 §4/§7.1、D-04 §4.5 | P0-01、P0-02、P0-08、P0-15、P0-31、P0-42 | A1/A2/A9/L1 | `DONE`（年级校验/引导/改年级确认与迁移回归、seed 幂等均已通过） |
| 数据访问范围控制 | D-03 §6 | D-03 §6 | P0-04、P0-10、P0-40 | A3/A4/A5/A6 | `DONE`（范围解析、学习域改造与越权专项测试已通过） |
| 权限校验与审计 | D-03 §8 | D-03 §8 | P0-05、P0-07、P0-32、P0-39 | A7/A8/A10 | `DONE`（审计/`/me`/Token 失效/前端路由守卫/权限矩阵用例已通过） |
| 家长绑定与未成年人合规 | D-03 §7.2、D-05 | D-03 §7.2/§10.2 | P0-09、P1-05 | A4 | `DONE`（绑定/同意校验与家长端页面（切换孩子、孩子学情、每日时长、青少年模式）已完成） |
| 学校/教师组织能力 | D-03 §7.3/§7.4/§10.3 | D-03 §7.3/§7.4/§10.3 | P1-01~P1-06 | A5/A6 | `DONE`（组织模型/API/角色变更/班级聚合/教师端页面已完成） |
| 教材绑定与选择入口 | D-04 §4/§5 | D-04 §4/§5 | P0-11、P0-12、P0-13、P0-34、P0-16 | L1/L2/L3 | `DONE`（服务端推荐/绑定/冲突检测与前端教材管理页已完成） |
| 学习首页与"下一步"入口 | D-04 §3/§6.6 | D-04 §3/§6.6 | P0-14、P0-33、P1-11 | L1/L14 | `DOING`（首页聚合接口与前端学习首页已完成，待 P1-11 推荐服务） |
| 知识点分层与学习路径 | D-02 学科方案、D-04 §6 | D-04 §6 | P0-17~P0-20、P0-35 | L4/L5 | `DONE`（四层结构、状态机与前端单元/知识点详情已完成） |
| 智能辅助练习 | D-02 学法、D-04 §7 | D-04 §7 | P0-21~P0-24、P0-36 | L6/L7/L8/L13 | `DONE`（服务端预览/组卷/会话/来源拆分 + 前端配置/预览/续答/结算已完成） |
| 单元测试 | D-04 §8.1~§8.5 | D-04 §8 | P0-25~P0-30、P0-37 | L9/L10/L11/L12 | `DONE`（服务端组卷/交卷/报告/回流 + 前端考试中心/限时答题/报告页已完成） |
| 期中/期末/模考 | D-04 §8.1~§8.5 | D-04 §8、D-03 §5.2 | P1-07~P1-10、P2-07 | L9~L12 | `DOING`（P1-07 蓝图组卷、P1-08 考试窗口与过期处理、P1-09 主观题自评已完成，待 P1-10 报告增强与 P2-07 模考） |
| 主观题与报告增强 | D-04 §7.5/§8.5 | D-04 §7.5/§8.5 | P1-09、P1-10 | L11 | `DOING`（P1-09 主观题自评已完成，待 P1-10 报告增强） |
| 推荐与学习闭环 | D-04 §2.2/§6.6 | D-04 §2.2/§6.6 | P1-11、P1-12 | 闭环验收 | `TODO` |
| 平台化与增强（RBAC/图谱/离线/AI） | D-03 §9.2、D-04 §14 | D-03 §9.2、D-04 §14 | P2-01~P2-10 | M4 | `TODO` |
| 上架合规与发布 | D-08 §3/§7 | D-08 §3/§6 | R-01~R-09、P0-05、P0-09、P1-05、P2-08 | 发布验收 | `TODO` |

**矩阵维护规则**：

1. 新增需求：先在对应设计文档补章节并升版本 → 在本矩阵新增一行 → 在 §3 台账新增任务（含依赖与验收映射）。
2. 需求变更：走 §4.2 CR 流程，更新"需求来源/设计方案"两列与任务状态。
3. 任务完成：同步更新"当前状态"列，并与 §5.1 快照、§6 里程碑保持一致。
4. 每次会话结束：核对本矩阵状态与台账是否一致；设计文档有改动时更新 §1.1 的"版本/最后核对"。

### 1.3 本文件的作用

1. **唯一任务台账**：所有开发任务在此登记，禁止口头/聊天记录替代。
2. **进度事实来源**：状态、实际工时、产出证据均以此为准。
3. **过程追溯依据**：需求变更、技术难点、阻塞与解决方案全部留痕。
4. **验收对照表**：每个任务对应设计文档的验收编号，便于逐项签署。
5. **需求—设计映射**：通过 §1.1 与 §1.2 可反查"需求出自哪、由谁实现、进展如何"。

### 1.4 角色与负责人代码

| 代码 | 角色 | 说明 |
|---|---|---|
| `PM` | 项目负责人 | 需求确认、优先级裁决、里程碑验收 |
| `AR` | 架构/后端 | 数据模型、API、算法、迁移 |
| `FE` | 前端 | Flutter 页面、交互、状态管理 |
| `QA` | 测试 | 接口/权限/真机/E2E/性能 |
| `CT` | 内容运营 | 教材、知识点、题库、试卷蓝图 |
| `ALL` | 协同 | 多人共同负责 |

> 当前执行模式：`AR`/`FE`/`QA` 由 Trae Agent 承担，`PM` 由用户承担（需求与验收），`CT` 由 Agent 生成 + `PM` 抽检。

### 1.5 状态定义与流转规则

| 状态 | 定义 | 进入条件 | 退出条件 |
|---|---|---|---|
| **待启动** `TODO` | 已登记，未开始 | 计划评审通过 | 开发人员领取并开始 |
| **进行中** `DOING` | 正在开发/测试 | 依赖任务全部 `DONE`；已建分支或已改代码 | 达成 DoD 并附证据 |
|  **已完成** `DONE` | 交付并通过验证 | DoD 全满足（代码 + 测试 + 证据） | 验收后一般不可回退；返工需走变更记录 |
| **阻塞中** `BLOCKED` | 无法继续推进 | 依赖未满足 / 环境故障 / 需求不明确 / 缺陷阻塞 | 阻塞解除后回到 `DOING` |

**流转约束**：

```
TODO ──领取──► DOING ──达成DoD──► DONE
                 │  ▲
              阻塞▼  │解除
                BLOCKED
DONE ──返工（需CR）──► DOING
```

- 禁止 `TODO → DONE` 跳步。
- 进入 `BLOCKED` 必须同时在[第四章问题记录](#四问题记录与解决方案)登记，注明影响与预计解除条件。
- 每日更新时必须同步：主台账、状态看板、变更记录、问题记录四处一致。

### 1.6 优先级定义

| 级别 | 含义 | 排期原则 |
|---|---|---|
| `P0` | 阻断主链路/合规风险 | 当前迭代必须完成 |
| `P1` | 核心体验与体系完整性 | P0 完成后进入 |
| `P2` | 增强与效率 | 按资源插入 |
| `P3` | 可选/长期 | 不占当前迭代 |

### 1.7 完成定义（DoD）

一个任务只有同时满足以下条件才可标记 `DONE`：

1. 代码已合入（或已写入工作区并通过检查）。
2. 相关单测/接口测试通过（后端 `pytest`，前端 `flutter test`）。
3. 静态检查通过（`ruff`/`dart analyze` 0 issue）。
4. 关键路径有可复现证据（接口响应、真机截图、日志片段）。
5. 对应设计文档验收项已勾选（见每任务 `验收映射`）。
6. 若涉及数据库：迁移脚本可在空库与存量库升级，且 `seed` 幂等。

---

## 二、基线：已完成能力（不计入本次新增工作）

| 编号 | 内容 | 状态 | 证据 |
|---|---|---|---|
| B-01 | M1 账号体系（注册/登录/JWT） | `DONE` | 现有 `/api/auth/*`，pytest 通过 |
| B-02 | 教材/章节/知识点/题目内容模型与种子（134 教材/112 章/170 KP/564 题） | `DONE` | `scripts/seed.py` 幂等运行 |
| B-03 | 掌握度 EMA、错题本 SM-2、自适应组卷、四题型判题 | `DONE` | `app/services/learning.py` + `tests/test_learn.py` |
| B-04 | 学习/错题本/我的 三 Tab 与答题闭环 | `DONE` | 真机冒烟记录（v0.3） |
| B-05 | Alembic 迁移与 SQLite 兼容 | `DONE` | `b3f1a2c77d8e` 迁移 |

> 基线已冻结。本次开发不重复实现上述能力，只在其上扩展。

---

## 三、任务台账

> **状态字段实时更新**；`实际(h)` 在任务完成时填写；`证据` 填 commit / 测试结果 / 截图路径。
> **总任务数**：77（开发 68：P0 43 + P1 15 + P2 10；发布 9：R-01~R-09）；**基线已完成**：5；**进行中**：0；**阻塞中**：0；**待启动**：77；**总预估工时**：676 h（开发 557 + 发布 119）。

### 3.1 阶段 P0：身份与学习主链路（当前迭代）

#### 3.1.1 数据与权限底座

| ID | 任务 | 负责人 | 预估(h) | 优先级 | 依赖 | 状态 | 实际(h) | 验收映射 | 证据 |
|---|---|---|---|---|---|---|---|---|---|
| P0-01 | 扩展 `users` 字段：`grade_group/semester/enrollment_year/region/token_version/grade_updated_at/graduated_at/teacher_subjects/grade_start/grade_end`；新增 `grade_histories` 表；迁移脚本（SQLite `batch_alter_table`） | AR | 6 | P0 | 无 | `DONE` | 3 | A2/A9 | `d7a9c3e5b210` 迁移；空库/存量库 upgrade→downgrade→upgrade 通过；存量回填 stage/grade_group；`tests/test_user_grade.py` 唯一约束+默认值用例通过 |
| P0-02 | 实现 `derive_stage/derive_grade_group` 与注册/资料更新校验（年级必填、学段一致性、选科限 10-12） | AR | 5 | P0 | P0-01 | `DONE` | 2 | A1/A2 | `app/core/grade.py`；注册返回 422 `GRADE_REQUIRED`/`STAGE_MISMATCH`/`ELECTIVE_ONLY_SENIOR`；pytest 29 passed |
| P0-03 | 权限常量表 `ROLE_PERMISSIONS`、`PERMISSION_SCOPE`；`require_permission`/`require_student_access` 依赖；`require_admin` 兼容改造 | AR | 8 | P0 | P0-01 | `DONE` | 5 | A8 | `app/core/permissions.py`（35 权限点+10 角色+范围映射）；`deps.py` 的 `require_permission`/`require_student_access`/`require_admin` 兼容；pytest 44 passed |
| P0-04 | 数据范围解析 `resolve_student_ids`（SELF/CHILD/CLASS/SCHOOL/ALL）与聚合脱敏工具 | AR | 6 | P0 | P0-03 | `DONE` | 4 | A3/A4/A5/A6 | `app/core/scope.py`（SELF/CHILD/SCHOOL/ALL 完整、CLASS 待 P1-01 返回空集安全默认）；`users.school_id` 迁移 `e1b2c3d4f5a6`；`mask_phone`；`tests/test_scope.py` 9 例；空库/存量库迁移通过 |
| P0-05 | 审计日志接入：登录失败、改角色、改年级、跨用户读取、导出（含 before/after） | AR | 4 | P0 | P0-03 | `DONE` | 2 | A10 | `app/services/audit.py`（detail JSON 含 before/after，1000 字截断）；登录失败/停用写 `auth.login_failed`/`auth.login_blocked`；`require_student_access` 跨用户读取写 `data.cross_user_read`；改角色/改年级/导出钩子随 P1-04/P0-08/P0-40 接入；`tests/test_audit.py` |
| P0-06 | `GET /api/auth/me` 扩展（`stage/grade_group/permissions`）与 `GET /api/auth/permissions` | AR | 3 | P0 | P0-03 | `DONE` | 2 | A8 | `MeOut`/`PermissionsOut`；`/auth/me` 返回 `stage/grade_group/permissions/scope`；`/auth/permissions` 独立查询；admin 兼容返回 `["*"]`/`ALL`；pytest 50 passed |
| P0-07 | JWT 增加 `ver`，角色/年级变更自增 `token_version`，旧 Token 失效 | AR | 3 | P0 | P0-01/P0-03 | `DONE` | 2 | A7 | `create_access_token` 写入 `ver`（旧 Token 无 `ver` 视为 0，兼容存量会话）；`get_current_user` 比对 `user.token_version`；`bump_token_version` 供角色/年级变更调用；`tests/test_token_version.py` 5 例 |
| P0-08 | 年级修改接口 `PUT /api/users/me/grade`（每学期限 1 次、二次确认令牌、影响提示） | AR | 5 | P0 | P0-02/P0-07 | `DONE` | 3 | A1/A9 | `api/routes/users.py`：428 `CONFIRM_REQUIRED` 返回影响提示与 10 分钟确认令牌，确认后写 `grade_histories(source=self)`、`user.grade.change` 审计并 `bump_token_version`（旧 Token 401 `TOKEN_REVOKED`）；每学期限 1 次（409 `GRADE_CHANGE_LIMIT`）；`tests/test_grade_change.py` 7 例 |
| P0-09 | 家长绑定：`ParentChildBinding` 状态机（pending/active/revoked）、确认/解除、儿童账号同意校验 | AR | 8 | P0 | P0-03 | `DONE` | 3 | A4 | `api/routes/family.py`（发起/确认/解除/我的孩子）；`services/family.py` `has_active_guardian`；`/auth/me` 增加 `guardian_consent`；`tests/test_family.py` 6 例 |
| P0-10 | 学习域接口范围改造：`stats`/`wrong-questions` 支持 `student_id`，越权返回 `SCOPE_DENIED` | AR | 6 | P0 | P0-04 | `DONE` | 3 | A3/A4 | `require_student_access` 支持多候选权限点并按角色范围择优；`stats` 支持 `learn:stats:self/child/class`，`wrong-questions` 支持家长查看已同意孩子；家长未选孩子返回 422 `STUDENT_ID_REQUIRED`；`tests/test_learn_scope.py` 7 例 |

#### 3.1.2 教材绑定与学习首页

| ID | 任务 | 负责人 | 预估(h) | 优先级 | 依赖 | 状态 | 实际(h) | 验收映射 | 证据 |
|---|---|---|---|---|---|---|---|---|---|
| P0-11 | 新增 `textbook_bindings` 表与迁移（唯一键、状态、学期归档） | AR | 4 | P0 | P0-01 | `DONE` | 1 | L2/L3 | `models/textbook.py`；迁移 `f2b3c4d5e6a7`（唯一键 `user+subject+semester+textbook`、索引 `user+subject+status`）；空库与 dev 库 upgrade/downgrade/upgrade 通过 |
| P0-12 | 教材推荐与自动绑定服务（深圳版本优先级、开课科目、幂等 upsert） | AR | 6 | P0 | P0-11 | `DONE` | 2 | L2/L3 | `services/textbook.py`：学段开课科目清单、版本名含"深圳"优先、`auto_bind` 幂等 upsert 并归档同学科旧版本；`manual_bind` 校验教材存在与学科匹配 |
| P0-13 | 教材 API：`GET /me/textbooks`、`POST /me/textbooks/auto-bind`、`POST /me/textbooks/bind`、`DELETE /me/textbooks/{id}`、`GET /me/textbooks/recommend` | AR | 6 | P0 | P0-12 | `DONE` | 2 | L2/L3 | `api/routes/textbooks.py`：五个接口全部可用，家长返回 403 `NOT_STUDENT`；`tests/test_textbook.py` 7 例 |
| P0-14 | 学习首页聚合接口 `GET /api/learn/home`（当前教材、今日计划、继续学习、推荐、待办考试） | AR | 8 | P0 | P0-13/P0-10 | `DONE` | 2 | L1/L14 | `api/routes/learn.py`：`/learn/home` 返回年级/学段/学期/区县、已绑定教材或推荐教材、`today_plan`（按学段练习量与时长）、`continue_learning`（最近答题回溯章节/知识点）、`recommendation`（复习→薄弱<40→40-70→继续→每日一练）、`pending_exams`；非学生 403 `NOT_STUDENT`；`tests/test_home.py` 6 例（无绑定推荐、绑定后展示、复习优先、薄弱/中等掌握度、家长拦截） |
| P0-15 | 学期切换与年级升级定时任务（2 月/9 月、幂等 `grade_histories`、跨学段确认） | AR | 8 | P0 | P0-08/P0-12 | `DONE` | 2 | A9/L3 | `services/promotion.py`：`switch_semester` 切换学期并归档旧学期教材、按新学期重绑；`promote_grades` 仅 9 月执行、按学年幂等（同生同学年只升级一次）、12 年级写 `graduated_at`、跨学段归档教材并要求重新确认、升级写历史与审计并失效旧 Token；`scripts/semester_jobs.py` 提供 cron/任务计划入口；`tests/test_promotion.py` 5 例 |
| P0-16 | 教材与年级冲突检测（`mismatch` 标记、接口告警、练习前拦截） | AR | 4 | P0 | P0-14 | `DONE` | 1 | L3/异常表 | 教材绑定返回 `mismatch`、首页返回 `mismatch_subjects` 与单本教材 `mismatch`；`/learn/start` 命中冲突返回 428 `TEXTBOOK_MISMATCH`，`confirm_mismatch=true` 后放行；`tests/test_mismatch.py` 3 例 |

#### 3.1.3 四点：知识点分层与练习

| ID | 任务 | 负责人 | 预估(h) | 优先级 | 依赖 | 状态 | 实际(h) | 验收映射 | 证据 |
|---|---|---|---|---|---|---|---|---|---|
| P0-17 | `knowledge_points` 增加 `node_type/order_index/weight`，存量数据兼容（空 `parent_id` 视为 point 并补"默认节"） | AR | 4 | P0 | P0-01 | `DONE` | 1 | L4 | `models/content.py` 新增三字段；迁移 `c3d4e5f6a7b8`（batch 加列 + 索引 + 存量补"默认节"并挂接，downgrade 可逆）；dev 库 upgrade/downgrade/upgrade 验证：237 行中 67 节 + 170 知识点，无孤儿、无自引用；`tests/test_kp_layers.py` 2 例 |
| P0-18 | 内容种子改造：生成"单元→节→知识点"四层结构（小学 1-3 完整，4-12 样章），保持幂等 | CT/AR | 12 | P0 | P0-17 | `DONE` | 2 | L4 | `scripts/seed.py`：每单元生成节节点并挂接知识点（`_put_section`/`_put_kp`）；修复节与知识点同名误匹配（限定 `node_type='point'`）；`_prune_default_sections` 清理迁移遗留空"默认节"；全新库 alembic+seed 连跑两次结果稳定（170 知识点 + 112 节，无自引用/孤儿/空节）；`tests/test_seed_layers.py` 3 例 |
| P0-19 | 单元/节/知识点接口：`GET /learn/textbook/{id}/units`、`GET /learn/unit/{chapterId}`、`GET /learn/kp/{id}`（含前置、状态、历史） | AR | 8 | P0 | P0-17/P0-18 | `DONE` | 2 | L4/L5 | `api/routes/learn.py`：单元列表（节数/知识点数/题量/平均掌握度/已学进度）、单元详情（节聚合 + 知识点节点状态）、知识点详情（前置掌握度、所属节、最近学习时间）；`services/learning.derive_study_state` 状态推导（未学习/待巩固/已掌握/复习中）；`tests/test_unit_tree.py` 4 例 |
| P0-20 | `kp_study_states` 表与状态机（未学习/学习中/待巩固/已掌握/复习中），讲解阅读与自测达标写入 | AR | 6 | P0 | P0-19 | `DONE` | 2 | L5 | `models/practice.KpStudyState` + 迁移 `d4e5f6a7b8c9`；`services/study_state.py` 状态迁移（read→学习中、practice→待巩固、selftest≥80→已掌握、revision→复习中）与幂等 upsert；接口 `POST /learn/kp/{id}/read`、`POST /learn/kp/{id}/selftest`；`/learn/submit` 自动写入；知识树/单元/知识点详情优先展示持久化状态、复习到期覆盖为"复习中"；`tests/test_study_state.py` 3 例 |
| P0-21 | 练习预览 `POST /learn/practice/preview`：题量、KP 覆盖、时长、seed，题量不足提示 | AR | 6 | P0 | P0-19 | `DONE` | 2 | L6/L8 | `services/practice.py`（`resolve_pool` 支持 kp/chapter/textbook/wrong 四范围、`select_questions` 确定性选题 + 到期错题配额 25% + 按知识点分桶轮转、`PracticePlan` 覆盖率/时长统计）；`POST /learn/practice/preview` 返回可用题量/是否不足/覆盖率/预估时长/题型分布/到期错题数/seed；`tests/test_practice_preview.py` 5 例（不足提示、章节/教材范围、题型过滤+同 seed 幂等、错题范围到期计数、非法范围 422）；修复分桶轮转在空桶时不推进游标导致的死循环 |
| P0-22 | 组卷算法扩展：题型配比、KP 覆盖≥80%、去重、时长预算、到期错题≤25% | AR | 10 | P0 | P0-21 | `DONE` | 3 | L6/L7 | `services/practice.py`：题型配比按学段（小学 40/20/25/15，初中/高中另设）与 `unit`/`pre_exam` 蓝图；覆盖目标 KP≤3 全覆、否则 ≥80%；7 天内已作答去重（过滤后为空回退全量）；到期错题 floor(25%) 且上限 5、只走配额；时长预算超限裁剪低难度非到期题；`/learn/start` 支持 `scope_type/scope_ids/q_types/mode/seed/duration_limit_min` 与预览同 seed 同题，旧参数兼容；`tests/test_practice_plan.py` 6 例 |
| P0-23 | `practice_sessions` 表与续答/结算：`POST /learn/sessions/{id}/finish`、`GET /learn/sessions/{id}` | AR | 7 | P0 | P0-22 | `DONE` | 3 | L13 | `models/practice.PracticeSession` + 迁移 `e5f6a7b8c9d0`（question_ids/scope JSON、计数、seed、起止时间）；`/learn/start` 新范围方式创建会话并返回 `session_id`；`GET /learn/sessions/{id}` 返回题目+已答状态+`next_index`（断点续答）；`POST .../finish` 汇总正确率/用时/知识点表现/错题数，重复调用幂等（保留首次 `finished_at`）；会话仅本人可见；`tests/test_practice_session.py` 5 例 |
| P0-24 | 练习提交兼容扩展：`session_id/source` 写入、掌握度来源拆分 | AR | 4 | P0 | P0-23 | `DONE` | 3 | L12 | `student_question_records` 增加 `source`（practice/review/exam）、`session_id`、`kp_weight` + 迁移 `f6a7b8c9d0e1`；`mastery_scores` 增加 `source_breakdown` JSON；`/learn/submit` 接受 `session_id`（归属校验 + 会话内题目校验）与 `source`，旧请求不变；`update_mastery` 支持来源与权重并累计来源明细；会话续答/结算优先按 `session_id` 归属（兼容无 session_id 的时间窗记录）；`tests/test_submit_session.py` 4 例 |

#### 3.1.4 单元测试闭环

| ID | 任务 | 负责人 | 预估(h) | 优先级 | 依赖 | 状态 | 实际(h) | 验收映射 | 证据 |
|---|---|---|---|---|---|---|---|---|---|
| P0-25 | `exam_blueprints` 表与单元测蓝图种子（小学数学/语文/英语各 1 套） | CT/AR | 8 | P0 | P0-17 | `DONE` | 3 | L9 | `models/exam.ExamBlueprint`（code/subject/grade/exam_type/total_score/time_limit_min/sections/kp_coverage_min/difficulty_mix/is_active）+ 迁移 `g7b8c9d0e1f2`；`scripts/seed.py` 新增 `_put_blueprint`（按 code 幂等）与 `EXAM_BLUEPRINT_SEEDS`（数学 计算30+填空20+选择20+解决问题30；语文 字词20+句子20+阅读30+习作30；英语 听力30+选择40+书写30，均为 60 min、覆盖率 0.8、难度 7:2:1）；`tests/test_exam_blueprint.py` 3 例（种子幂等、分值合计=100、更新不新增） |
| P0-26 | 试卷生成服务（蓝图 + seed 稳定、题型/难度/覆盖约束、题量兜底） | AR | 10 | P0 | P0-25/P0-22 | `DONE` | 3 | L9 | `services/exam_paper.py`（`generate_paper` 分节按题型+难度优先选题、知识点覆盖优先、跨节去重、题型不足时按任意剩余题兜底并记录 `fallback_count`、`ExamPaper` 输出题目/分值/覆盖率/难度分布/题量不足标记）；同 seed 完全确定；`tests/test_exam_paper.py` 5 例（蓝图一致性 36 题/100 分、seed 可复现、难度优先、兜底 26 题、题量不足） |
| P0-27 | `exams` 扩展 + `exam_attempts`/`exam_answers` 表与迁移 | AR | 6 | P0 | P0-01 | `DONE` | 3 | L10 | `Exam`（模型）扩展 `blueprint_id/exam_type/chapter_ids/status`；新增 `ExamAttempt`（user/exam/seed 唯一、status、起止时间、客观/主观/总分、submit_token）与 `ExamAnswer`（attempt+question 唯一、user_answer/is_correct/score/self_score）；迁移 `h8c9d0e1f2g3`；`tests/test_exam_schema.py` 4 例（默认值、作答往返、两级唯一约束） |
| P0-28 | 考试接口：开始/续答、3 秒防抖保存、交卷幂等、客观自动判 | AR | 10 | P0 | P0-26/P0-27 | `DONE` | 4 | L10/L11 | `app/schemas/exam.py` + `app/api/routes/exams.py`（列表按用户年级与作答状态分类、详情不含答案、`POST /exams/{id}/attempts` 复用进行中作答/超时强制交卷、`PATCH /exams/attempts/{id}` 幂等 upsert、`POST .../submit` 按 `submit_token` 幂等且客观题自动判/主观题转 `grading`、`POST /exams/generate` 按蓝图组卷）；`main.py` 注册路由；`tests/test_exam_api.py` 8 例；全量 pytest 148 passed |
| P0-29 | 考试报告：总分、题型得分、KP 得分率、错题清单、下一步入口 | AR | 8 | P0 | P0-28 | `DONE` | 3 | L11/L12 | `GET /api/exams/attempts/{id}/report`（未交卷 409 `EXAM_NOT_SUBMITTED`；输出总分/满分、客观/主观得分、正确率、题型得分率、知识点得分率、错题清单与正确解析、`weak_practice`/`wrong_review`/`retake` 下一步）；`tests/test_exam_report.py` 4 例；全量 pytest 152 passed |
| P0-30 | 考试数据回流：错题入库、掌握度按考试权重更新（单元测 0.8） | AR | 4 | P0 | P0-29 | `DONE` | 3 | L12 | `student_question_records.attempt_id`（迁移 `i9d0e1f2g3h4`）；交卷 `_finalize` 对客观题写入 `source=exam` 答题记录（含 `kp_weight`）、`WrongQuestion`（默认 `wrong_reason=other`）与掌握度 EMA（单元测 0.8 / 期中 0.6 / 期末 0.5），主观题不回流；幂等交卷不重复入库；`tests/test_exam_backflow.py` 3 例；全量 pytest 155 passed |

#### 3.1.5 前端 P0

| ID | 任务 | 负责人 | 预估(h) | 优先级 | 依赖 | 状态 | 实际(h) | 验收映射 | 证据 |
|---|---|---|---|---|---|---|---|---|---|
| P0-31 | 登录后年级引导页（3 步：学段→年级→教材确认），未完成强制拦截 | FE | 10 | P0 | P0-06/P0-08/P0-13 | `DONE` | 4 | L1 | 新增 `core/models/textbook_binding.dart`、`textbook_service.dart`（绑定/推荐/自动绑定）、`user_service.dart`（年级变更 428 二次确认）；`api_client` 增加 `putJson` 与结构化 `payload`；`features/onboarding/entry_gate_page.dart`（按绑定状态放行/拦截）+ `onboarding_page.dart`（学段→年级→教材推荐三步）；`app.dart` 路由守卫 + 登录后进入 `/gate`；`dart analyze lib test` 0 issues、`flutter test` 8 passed |
| P0-32 | 路由守卫 + `PermissionGate` + 403 错误统一处理（按业务码给引导） | FE | 6 | P0 | P0-03/P0-06 | `DONE` | 3 | A8 | 新增 `core/errors/api_error_guide.dart`（`TOKEN_REVOKED`→重登、`PERMISSION_DENIED`/`SCOPE_DENIED`→无权限文案、`GRADE_REQUIRED`/`GRADE_MISSING`→引导页、401/403 兜底）；`features/common/permission_gate.dart`（`anyOf` 任一命中放行、超管 `*` 直通、`ForbiddenPage` 返回/回首页）；`app.dart` 未登录统一跳 `/login`，`/shell`/`/home` 需 `learn:content:read`、`/knowledge/*` 需 `learn:kp:study`、`/session`/`/practice/*` 需 `learn:practice:start`；各页错误统一走 `ApiErrorGuide`/`handleApiError`；`dart analyze lib test` 0 issues、`flutter test` 8 passed |
| P0-33 | 学习首页重构：当前教材卡、今日计划、继续学习、学科入口、考试入口 | FE | 12 | P0 | P0-14 | `DONE` | 4 | L1/L15 | `core/models/learn.dart` 新增 `HomeData/HomeTextbook/HomeTodayPlan/HomeContinue/HomeRecommendation`（`textbookOf`/`stageEnum`/学期与学科标签）；`learn_service.home()` 接入 `GET /api/learn/home`；`features/learn/learn_page.dart` 重构为学生首页聚合（推荐下一步卡、今日计划三项可点、继续学习、学科入口教材卡含年级冲突标识、考试入口占位）与家长非学生教材章节浏览降级；未绑定教材展示推荐与 `/gate` 绑定入口；`learn_model_test.dart` 新增 HomeData 2 例；`dart analyze lib test` 0 issues、`flutter test` 10 passed |
| P0-34 | 教材管理页：学科/学期切换、版本选择、推荐标识、冲突二次确认、解绑 | FE | 8 | P0 | P0-13 | `DONE` | 4 | L2/L3 | 新增 `features/textbook/textbook_manage_page.dart`（学科 Chip、上册/下册切换、推荐标识、使用中高亮、年级不一致二次确认、解绑确认与空态）；`textbook_service` 增加 `bind/unbind`，`api_client` 增加 `deleteJson`，`/textbooks` 路由 + 学习首页/我的页入口；后端 `manual_bind` 绑定学期改为以教材为准并跨学期归档同学科旧绑定（`tests/test_textbook.py` 新增 1 例）；`dart analyze lib test` 0 issues、`flutter test` 10 passed、`pytest` 156 passed |
| P0-35 | 单元/节/知识点树与详情页（掌握度环、状态、前置跳转、讲解/例题） | FE | 12 | P0 | P0-19/P0-20 | `DONE` | 6 | L4/L5 | `knowledge_page` 改为单元目录（掌握度环/进度/节·知识点·题量），新增 `unit_page`（节分组、知识点状态与练一练、单元综合练习）、`kp_detail_page`（讲解/前置跳转/状态/掌握置信度/例题带答案解析/我已理解）、`mastery_ring` 通用组件；`learn_service` 增加 units/unitDetail/kpDetail/kpExamples/markKpRead，模型增加 UnitSummary/UnitSection/UnitDetail/KpBrief/KpDetail/KpExample；后端新增 `GET /learn/kp/{id}/examples`（最多 2 道，带答案解析，`tests/test_unit_tree.py` 新增 1 例）；路由 `/unit/:id`、`/kp/:id`；`dart analyze` 0 issues、`flutter test` 10 passed、`pytest` 157 passed |
| P0-36 | 练习配置页 + 预览 + 答题页扩展（模式、续答、结算、下一步） | FE | 12 | P0 | P0-21/P0-23 | `DONE` | 8 | L8/L13 | 新增 `practice/config` 配置页（专项/同步/考前模式、知识点/单元/整册范围、题量、题型、组卷预览与不足提示）；`session_page` 扩展范围组卷（同 seed 预览=实际）、428 教材年级冲突二次确认、断点续答（`/session?session=id`）、提交带 `session_id/source`、结算页（正确率/用时/错题/知识点表现/下一步）；首页增加「继续上次练习」入口（本地草稿 `practice_last_session`）；模型新增 PracticePreview/PracticeStartResult/PracticeSessionData/PracticeFinish；`dart analyze` 0 issues、`flutter test` 10 passed、`pytest` 157 passed |
| P0-37 | 考试中心列表、考试详情/答题（计时、自动保存、交卷确认）、报告页 | FE | 16 | P0 | P0-28/P0-29 | `DONE` | 10 | L10/L11 | 新增 `core/models/exam.dart`（ExamSummary/ExamAttempt/ExamReport/题型与知识点统计/错题与下一步）、`exam_service.dart`（列表/开始续答/防抖保存/交卷/报告）、`api_client` 增加 `patchJson`；新增 `features/exam/exam_list_page.dart`（待考/进行中/已完成分类、开始/继续/查看报告）、`exam_page.dart`（倒计时、答题卡、3 秒防抖自动保存、交卷确认、超时自动交卷、退出保留计时）、`exam_report_page.dart`（总分/正确率/用时、题型得分率、知识点得分率与跳转、错题清单与解析、薄弱点专项/错题重练/再考一次下一步）；路由 `/exams`、`/exam/:examId`（`learn:exam:take`）、`/exam/report/:attemptId`（`learn:exam:report:self`），学习首页考试入口改为跳转考试中心；`exam_model_test.dart` 3 例；`dart analyze` 0 issues、`flutter test` 13 passed、`pytest` 157 passed |
| P0-38 | 前端单测/组件测试补充（模型解析、状态机、守卫） | FE/QA | 8 | P0 | P0-31~P0-37 | `DONE` | 4 | L15 | 新增 `permission_gate_test.dart`（命中任一权限放行、无权限 403、超管 `*` 直通、未登录 fallback、`anyOf` 为空不限制 + `AppUser` 权限判定 5 例组件测试）；`api_error_guide_test.dart` 5 例（`TOKEN_REVOKED`/`PERMISSION_DENIED`/`GRADE_REQUIRED`/401/403 兜底/普通文案）；`practice_session_model_test.dart` 4 例（预览、开始、会话续答、结算知识点表现）；`textbook_binding_model_test.dart` 4 例（绑定/推荐/学段映射）；累计前端测试 32 例全部通过、`dart analyze` 0 issues |

#### 3.1.6 测试与验收 P0

| ID | 任务 | 负责人 | 预估(h) | 优先级 | 依赖 | 状态 | 实际(h) | 验收映射 | 证据 |
|---|---|---|---|---|---|---|---|---|---|
| P0-39 | 后端单测：年级派生、权限矩阵、范围解析、组卷约束、考试幂等 | QA/AR | 12 | P0 | P0-01~P0-30 | `DONE` | 6 | A1~A10/L6~L12 | 新增 `test_exam_guards.py` 9 例（跨年级 403/未发布隐藏、列表分类与类型过滤、超时自动结算后新建、过期保存自动交卷、交卷后 PATCH 只读、seed 冲突、报告需交卷且仅本人、报告题型/知识点统计、作答归属）；扩充 `test_grade_rules.py` 5 例（1~12 年级全矩阵、越界错误码、学段校验、选科限制、学年/学期边界）；扩充 `test_permissions.py` 4 组（9 角色权限矩阵、超管全量、权限目录一致性、权限→范围矩阵）；扩充 `test_scope.py` 5 例（CLASS 安全空集、未知范围、无绑定、ALL、跨权限拒绝）；后端测试 203 passed |
| P0-40 | 越权专项测试：跨学生、跨班级、跨学校、pending 绑定、旧 Token | QA | 6 | P0 | P0-39 | `DONE` | 4 | A3~A7 | 新增 `test_access_control.py` 7 例（跨学生统计/错题 403、教师跨班级 SCOPE_DENIED 且不可参加考试、跨学校范围解析与接口拒绝、pending 绑定错题 403、家长不可参加考试/不可读未绑定孩子、家长不可读已绑定孩子考试报告、旧 Token 在 `/auth/me` `/learn/home` `/exams` 均 `TOKEN_REVOKED`）；后端测试 210 passed |
| P0-41 | 真机 E2E：年级引导→首页→四层下钻→练习→单元测→报告→错题复习 | QA | 8 | P0 | P0-31~P0-38 | `DONE` | 6 | L1~L15 | 新增 `app/integration_test/learning_e2e_test.dart`（真机 integration_test：注册/登录→三步年级引导→首页→数学教材→单元→知识点→练一练→练习配置（取消填空题）→答题与结算→错题本→管理员生成单元测→考试中心→限时答题→交卷→报告→返回考试中心校验「查看报告/得分」）；`app/android/app/build.gradle.kts` 增加 `configurations.all { resolutionStrategy { force(...) } }` 将 espresso/test 依赖升到 3.5.1/1.5.x，解决 AGP 8 下 `androidx.test.espresso` namespace 冲突；设备 `66B0219C18003002`（OXF AN10 / Android 12）执行 `flutter test --no-pub integration_test/learning_e2e_test.dart -d <device>` 全部通过（All tests passed）；`dart analyze lib test integration_test` 0 issues |
| P0-42 | 迁移/种子回归：空库升级、存量库升级、seed 二次幂等 | QA/AR | 4 | P0 | P0-18/P0-25 | `DONE` | 2 | A9/基线约束 | 新增 `backend/tests/test_migrations.py` 3 例：①空库 `upgrade head → downgrade base → upgrade head`（head `i9d0e1f2g3h4`、19 张核心表齐全、降级后仅剩 `alembic_version`）；②存量库（`b3f1a2c77d8e` + 学生数据 `grade=4`）升级 head 后数据保留，回填 `stage=primary`/`grade_group=primary_mid`/`token_version=0`/默认 `region=shenzhen`/`semester=first` 并生成 `grade_histories`；③`scripts.seed` 连跑两次行数完全一致（users 9 / textbooks 134 / chapters 112 / knowledge_points 282 / questions 564 / exam_blueprints 3）且无重复账号；另在 `ailearning_dev.db` 副本上执行 `alembic upgrade head` + 双跑 seed 复核一致；`ruff check tests/test_migrations.py` 通过，`pytest` 213 passed |
| P0-43 | P0 里程碑验收与文档同步（更新本计划、设计文档差异） | PM | 3 | P0 | P0-39~P0-42 | `DONE` | 3 | M2.5 | 汇总复核 P0-01~P0-42 台账；`pytest` 213 passed、`ruff check` 0 issue、`flutter analyze --no-pub` 0 issues、`flutter test --no-pub` 32 passed；§6.1 A10 调整为部分完成（改角色审计随 P1-04、导出审计随 P2-08）、L6/L7 转 `DONE`；§4.1 I-001/I-002 转 `RESOLVED`；§1.1 D-03/D-04 状态更新为「部分生效（P0 已落地）」；新增 §6.2 M2.5 验收记录；M2.5 技术验收通过待 PM 签署 |

> **P0 小计**：43 项，预估 **310 h**（AR 173、FE 84、CT 20、QA 30、PM 3；CT/AR 协同任务按主责计一次）。

### 3.2 阶段 P1：角色扩展与综合考试

| ID | 任务 | 负责人 | 预估(h) | 优先级 | 依赖 | 状态 | 实际(h) | 验收映射 | 证据 |
|---|---|---|---|---|---|---|---|---|---|
| P1-01 | 教师/班主任/校管角色与 `schools/classes/class_members/teacher_class_assignments` 表 | AR | 10 | P1 | P0-03 | `DONE` | 3 | A5/A6 | 新增 `app/models/org.py`（`School`/`SchoolClass`/`ClassMember`/`TeacherClassAssignment`，班级唯一键 `school_id+grade+name`、授课唯一键 `teacher_id+class_id+subject`）；迁移 `j0e1f2g3h4i5`（4 表 + 索引，空库与 `ailearning_dev.db` 副本升级通过）；`scope.py` 的 CLASS 范围接入：班主任 `head_teacher_id`/`role_in_class` 全学科可见，科任教师按 `subject` 收窄，跨校与未绑定学校安全返回空集；`tests/test_org.py` 4 例（学科收窄、班主任全科、跨校/未绑定拒绝、复合唯一约束）；`pytest` 217 passed |
| P1-02 | 班级与授课分配 API、教师年级/学科范围校验 | AR | 8 | P1 | P1-01 | `DONE` | 2 | A5 | `api/routes/org.py`：`GET/POST /org/schools`（超管）、`GET/POST /org/classes`（校管按本校、教师按授课班）、`GET/POST /org/classes/{id}/members`（批量入班，校验学生角色/同校/年级一致、重复入班幂等）、`GET/POST /org/assignments`（校验教师角色、同学段、`teacher_subjects`、`grade_start/grade_end`，班主任冲突/重复分配 409）；`schemas/org.py`；`deps.require_any_permission`；审计 `org.school.create/class.create/member.add/teacher.assign`；`tests/test_org_api.py` 3 例（班级/成员/教师可见性、跨校与角色拒绝、分配规则与冲突）；`pytest` 220 passed |
| P1-03 | 班级学情聚合接口（仅聚合值，不泄露逐题原文） | AR | 8 | P1 | P1-02/P0-04 | `DONE` | 2 | A5/6.5 | `GET /api/org/classes/{id}/stats`：返回学生数/近 7 日活跃数与提交率、答题数与正确率、平均掌握度、薄弱知识点 Top5（班级均值），支持 `subject` 收窄；教师按授课班+学科校验，校管限本校，越权 `SCOPE_DENIED`；响应不含任何学生标识与逐题原文；`tests/test_org_stats.py` 2 例（聚合口径与字段白名单、教师/校管/学生/跨校范围）；`pytest` 222 passed |
| P1-04 | 管理端用户列表与角色授予/回收（禁止自授超管、本校范围） | AR | 8 | P1 | P1-01 | `DONE` | 3 | A6/A8 | `api/routes/admin_users.py`：`GET /admin/users`（分页/角色/学校/年级/关键词筛选，校管强制本校，手机号脱敏）；`POST /admin/users/{id}/roles`（grant/revoke 单角色，`SELF_ROLE_DENIED` 禁自改与自授超管、校管仅可授予学生/教师/班主任且限本校、`ROLE_MISMATCH`/`ROLE_INVALID`/`ROLE_CONFLICT`）；角色变更 `bump_token_version` 旧 Token 401 `TOKEN_REVOKED`；审计 `admin.role.assign` 含 before/after；`tests/test_admin_users.py` 4 例；`pytest` 226 passed、`ruff` 0 issue |
| P1-05 | 家长端页面：切换孩子、孩子学情、时长与青少年模式 | FE | 12 | P1 | P0-09 | `DONE` | 3 | A4 | 后端：`users.teen_mode` 字段（迁移 `k1f2g3h4i5j6`）、`GET /family/children` 返回 `daily_limit_minutes/teen_mode`、`PUT /family/children/{id}/controls`（空字段 422 `CONTROLS_REQUIRED`、无 active 绑定 404、审计 `family.controls.update`），`tests/test_family_controls.py` 2 例；前端：`FamilyChild` 模型、`FamilyService`、`ParentChildrenPage`（ChoiceChip 切换孩子、按 `student_id` 拉取学情、时长滑块 0~240、青少年模式开关、保存提示）、`/family` 路由 + `PermissionGate`、个人中心家长入口，非学生账号不再请求个人统计；`family_model_test.dart` 2 例、`parent_children_page_test.dart` 4 例；`flutter analyze --no-pub` 0 issues、`flutter test --no-pub` 38 passed、`pytest` 228 passed、`ruff` 0 issue |
| P1-06 | 教师端页面：班级概览、班级报告（聚合） | FE | 12 | P1 | P1-03 | `DONE` | 3 | A5 | 前端：`ClassSummary`/`ClassStats`/`ClassWeakPoint` 模型、`OrgService`（`GET /org/classes`、`GET /org/classes/{id}/stats` 支持 `subject`）、`TeacherClassesPage`（班级卡片/空态/下拉刷新）、`ClassStatsPage`（学生数/近 7 日活跃/正确率/平均掌握度/提交率/薄弱 Top5，页面明示仅聚合数据）、`/teacher/classes` 与 `/teacher/classes/:classId/stats` 路由 + `PermissionGate`、个人中心教师入口；`org_model_test.dart` 3 例、`teacher_pages_test.dart` 3 例；`flutter analyze --no-pub` 0 issues、`flutter test --no-pub` 44 passed |
| P1-07 | 期中/期末蓝图与组卷（范围=章节集合、6:3:1 难度、KP 覆盖） | CT/AR | 10 | P1 | P0-26 | `DONE` | 3 | L9 | 蓝图：`scripts/seed.py` 新增 6 套期中/期末蓝图（语数英各 2 套，`exam_type=midterm/final`，`sections` 按 `band` 分带，得分 60/30/10，`kp_coverage_min=0.8`，时限 90 分钟）；组卷：`app/services/exam_paper.py` 支持 `band → difficulty` 映射（easy 1 / medium 2~3 / hard 4~5）；`tests/test_exam_comprehensive.py` 4 例（蓝图规格、两章范围组卷得分 60/30/10 且覆盖 6/6 KP、同 seed 幂等、`/api/exams/generate` 发布 midterm 试卷）；`tests/test_exam_blueprint.py` 同步 9 套蓝图断言；`pytest` 232 passed |
| P1-08 | 考试中心扩展：期中/期末/模考入口、考试窗口与过期处理 | AR/FE | 10 | P1 | P0-37/P1-07 | `DONE` | 3 | L10 | 后端：`exams.window_start/window_end`（迁移 `l2g3h4i5j6k7`）、`/api/exams/generate` 支持窗口配置、列表返回 `window_state`（open/scheduled/closed/unscheduled）、窗口外开考 403 `EXAM_WINDOW_NOT_OPEN/EXAM_WINDOW_CLOSED`、保存/交卷遇窗口关闭按已存答案自动交卷且不再接收新答案，`tests/test_exam_window.py` 3 例；前端：`ExamSummary` 窗口字段与 `windowLabel/windowRange`、考试列表新增类型筛选（单元测/期中/期末/模考）、窗口时间与状态展示、未开放时提示拦截，`exam_model_test.dart` +1 例、`exam_list_page_test.dart` 2 例；`pytest` 235 passed、`flutter analyze --no-pub` 0 issues、`flutter test --no-pub` 47 passed |
| P1-09 | 主观题自评：参考答案、评分点、自评量表、成绩回写 | AR/FE | 10 | P1 | P0-29 | `DONE` | 3 | L11 | 后端：报告新增 `pending_subjective`（题干/作答/参考答案/`scoring_points`/解析/原自评分）、`POST /exams/attempts/{id}/self-assess`（未交卷 409、重复题/非主观题/超满分 422、题目不在卷 404；首次自评按 60% 及格线写 `StudentQuestionRecord`、掌握度 EMA 与错题本，重评不重复回流；按试卷重算主观分与总分，`pending_count==0` 转 `completed`），`tests/test_exam_self_assess.py` 4 例；前端：`ExamSubjectiveQuestion` 模型与 `pending_subjective` 解析、`ExamService.selfAssess`、报告页新增「主观题自评」卡（参考答案/评分点/解析/0~满分滑块/提交后刷新），`exam_model_test.dart` +1 例、`exam_report_page_test.dart` 1 例；`pytest` 239 passed、`flutter analyze --no-pub` 0 issues、`flutter test --no-pub` 49 passed |
| P1-10 | 报告增强：能力维度雷达、班级平均（有班级时）、趋势对比 | AR/FE | 8 | P1 | P1-09/P1-03 | `TODO` | — | L11 | — |
| P1-11 | 推荐服务：今日计划生成规则（复习→薄弱→单元测→进度→每日一练） | AR | 8 | P1 | P0-14/P0-20 | `TODO` | — | 6.6 | — |
| P1-12 | 错题与考试联动优化：考试错题错因默认分类、复习优先级 | AR | 4 | P1 | P0-30 | `TODO` | — | L12 | — |
| P1-13 | 性能优化：首页聚合缓存、学情统计缓存失效策略 | AR | 6 | P1 | P0-14 | `TODO` | — | L14 | — |
| P1-14 | P1 测试与真机回归 | QA | 12 | P1 | P1-01~P1-13 | `TODO` | — | — | — |
| P1-15 | P1 里程碑验收与计划同步 | PM | 3 | P1 | P1-14 | `TODO` | — | — | — |

> **P1 小计**：15 项，预估 **129 h**。

### 3.3 阶段 P2：平台化与增强

| ID | 任务 | 负责人 | 预估(h) | 优先级 | 依赖 | 状态 | 实际(h) | 验收映射 | 证据 |
|---|---|---|---|---|---|---|---|---|---|
| P2-01 | RBAC 表上线（`roles/permissions/role_permissions/user_roles`）与双写/对账 | AR | 12 | P2 | P1-04 | `TODO` | — | 9.2 | — |
| P2-02 | 权限配置后台（角色-权限可视化） | AR/FE | 12 | P2 | P2-01 | `TODO` | — | 9.1 | — |
| P2-03 | 教师布置作业/班级统一卷、批改主观题 | AR/FE | 16 | P2 | P1-09/P1-02 | `TODO` | — | 8.1/5.2 | — |
| P2-04 | 知识图谱视图（前置依赖可视化、薄弱高亮） | FE | 10 | P2 | P0-19 | `TODO` | — | 6.2 | — |
| P2-05 | 图片作答与离线整卷（本地队列、断网重放） | FE/AR | 16 | P2 | P0-23 | `TODO` | — | 13 章 | — |
| P2-06 | AI 讲解与错题归因辅助（LLM 接入、Prompt 安全） | AR | 16 | P2 | P0-19 | `TODO` | — | 6.4 | — |
| P2-07 | 模考与真题库、考试窗口与公平性（同班同卷） | CT/AR | 12 | P2 | P1-08 | `TODO` | — | 8.3 | — |
| P2-08 | 数据导出与合规审计增强（脱敏导出、用途登记） | AR | 6 | P2 | P0-05 | `TODO` | — | A10 | — |
| P2-09 | 内容审核双人复核流程 | AR/FE | 8 | P2 | P0-05 | `TODO` | — | 5.3 | — |
| P2-10 | P2 回归与验收 | QA/PM | 10 | P2 | P2-01~P2-09 | `TODO` | — | — | — |

> **P2 小计**：10 项，预估 **118 h**。

### 3.4 发布与合规任务（R，来源 D-08）

> 本组任务来自 [release-plan.md](./release-plan.md) §3 的 8 项上架缺口，按"可执行项"拆分。**发布任务不重复开发任务**：凡与 P0/P1/P2 重叠的，以开发任务为实施主体，R 任务负责补齐商店与法规硬性要求并做发布验收。

| ID | 任务（可执行项） | 负责人 | 预估(h) | 优先级 | 依赖 | 状态 | 实际(h) | 缺口/验收 | 证据 |
|---|---|---|---|---|---|---|---|---|---|
| R-01 | 正式签名与构建纪律：生成 release keystore（`make-release-keystore.ps1`）+ 备份；`build.gradle.kts` release 缺 keystore 时 fail-fast（禁止回退 debug）；统一 Android/HarmonyOS `versionCode` 规则（`1.0.0+1 → 10001`）；导出签名 MD5/SHA-256；AGC 正式签名证书与 Profile | AR | 5 | P0 | 无 | `TODO` | — | 缺口1 / R-A1 | — |
| R-02 | 后端生产化部署：云主机 + 域名 + HTTPS；切 PostgreSQL + `alembic upgrade head` + `seed.py`；密钥环境变量化；CORS 白名单、登录/注册限流、错误脱敏；每日备份与恢复演练；审计日志留存 ≥6 个月 | AR | 16 | P0 | 无 | `TODO` | — | 缺口3 / R-A2 | — |
| R-03 | 隐私政策公网发布 + App 内法务与同意链路：后端 `GET /legal/privacy`、`/legal/terms`（HTTPS、免登录）；「我的」页新增隐私政策/用户协议/联系我们；首启 ConsentGate（主动勾选、拒绝退出、无网络请求）；儿童注册监护人确认；政策版本升高重新同意并留痕 | AR/FE | 20 | P0 | R-02 | `TODO` | — | 缺口2 / R-A3 | — |
| R-04 | 商店硬性合规功能：账号注销（15 个工作日删除/匿名化）+ 数据导出（最小可用版）；家长绑定与 `consent_at` 生效；`daily_limit_minutes` 青少年模式生效；敏感操作审计（完整脱敏导出与用途登记仍由 P2-08 承接） | AR/FE | 20 | P0 | P0-05、P0-09 | `TODO` | — | 缺口8 / R-A4 | — |
| R-05 | 软著申请：整理源码 60 页（`app/lib` + `backend/app`）+ 操作说明书 + CPCC 线上提交（加急）+ 登记号归档（名称建议"深爱学学习辅助软件"） | PM/CT | 12 | P1 | 无（第 1 天启动） | `TODO` | — | 缺口5 / R-A5 | — |
| R-06 | 备案：域名 ICP 备案 → 导出签名 MD5 → 华为/小米商店侧 APP 备案（包名、签名、隐私 URL、SDK"无"）→ 备案号回填后端并在关于页展示 → 固化包名/签名不可变更 | PM/AR | 8 | P1 | R-01、R-03、R-05 | `TODO` | — | 缺口4 / R-A6 | — |
| R-07 | 内容版权与教育合规：建立《题源与授权台账》（来源/授权凭证/录入/审核）；商店与 App 内免责声明；删除"官方教材/名师/提分/押题"表述；举报入口与 24h 下架流程演练 | CT/AR/FE | 16 | P0 | P0-18 | `TODO` | — | 缺口6 / R-A7 | — |
| R-08 | 商店素材与合规表单：图标/特性图/截图（无教材封面与真实学生信息）、文案模板适配；Data Safety、目标受众与 Families、IARC 分级、华为隐私标签 | PM/QA | 12 | P1 | R-03 | `TODO` | — | 缺口7 / R-A8 | — |
| R-09 | 发布流水线与监控：`ci.ps1`（analyze/pytest/flutter test → build APK/AAB/HAP → `apksigner` 校验 → 产物归档 → git tag）；接入崩溃与错误监控；发布检查表自动化 | AR/QA | 10 | P2 | R-01 | `TODO` | — | 缺口8 / R-A9 | — |

> **R 小计**：9 项，预估 **119 h**（P0 5 项 77 h；P1 3 项 32 h；P2 1 项 10 h）。

#### 3.4.1 缺口 → 任务映射（发布验收口径）

| release-plan 缺口 | 对应 R 任务 | 关联开发任务 | 验收编号 |
|---|---|---|---|
| 缺口 1 正式签名与构建纪律 | R-01 | — | R-A1 |
| 缺口 2 隐私 URL + App 内同意链路 | R-03 | P0-05、P0-09（同意/审计底座） | R-A3 |
| 缺口 3 后端生产化部署 | R-02 | — | R-A2 |
| 缺口 4 APP 备案 | R-06 | — | R-A6 |
| 缺口 5 软件著作权 | R-05 | — | R-A5 |
| 缺口 6 内容版权与教育合规 | R-07 | P0-18（四层内容种子） | R-A7 |
| 缺口 7 商店素材与合规表单 | R-08 | — | R-A8 |
| 缺口 8 产品侧合规功能与发布工程 | R-04、R-09 | P0-05、P0-09、P1-05（完整增强另见 P2-08） | R-A4/R-A9 |

**发布验收编号（R-A1~R-A9）**

| 编号 | 判定标准 |
|---|---|
| R-A1 | 删除 `keystore.properties` 后 release 构建**失败**；有签名时 `apksigner` 证书 CN=AiLearning；Android 与 HarmonyOS `versionCode` 相同；MD5 已归档 |
| R-A2 | 公网 `https://<域名>/health` 返回 200；明文 HTTP 被客户端拒绝；备份可恢复演练通过；审计日志留存 ≥6 个月 |
| R-A3 | 隐私 URL 公网可直接打开且与 App 内一致；首启必须主动勾选才能进入；拒绝同意后无任何网络请求；政策版本升级触发重新同意且留痕 |
| R-A4 | 注销入口可用并在 15 个工作日内完成；数据导出可用；儿童账号无 `active` 绑定 + `consent_at` 时功能受限；时长上限生效；敏感操作全部审计留痕 |
| R-A5 | 取得软著受理号/证书，登记号归档 |
| R-A6 | APP 备案号下发并在 App 关于页展示；包名/签名与备案一致 |
| R-A7 | 题源台账覆盖首批内容；免责声明上线；举报入口可用；24h 下架流程演练通过 |
| R-A8 | 素材无版权/隐私瑕疵；Data Safety、Families、IARC、华为隐私标签均提交 |
| R-A9 | 一条命令完成 analyze/test/build/签名校验/tag；产物可追溯；崩溃监控有数据 |

### 3.5 依赖关系图（P0 与发布）

```mermaid
flowchart TD
    P001[P0-01 数据字段/年级历史] --> P002[P0-02 年级派生校验]
    P001 --> P003[P0-03 权限常量/依赖]
    P003 --> P004[P0-04 数据范围解析]
    P003 --> P005[P0-05 审计日志]
    P003 --> P006[P0-06 me/permissions]
    P001 --> P007[P0-07 JWT ver]
    P002 --> P008[P0-08 改年级接口]
    P003 --> P009[P0-09 家长绑定]
    P004 --> P010[P0-10 学习域范围改造]
    P001 --> P011[P0-11 textbook_bindings]
    P011 --> P012[P0-12 推荐/自动绑定]
    P012 --> P013[P0-13 教材 API]
    P010 --> P014[P0-14 首页聚合]
    P013 --> P014
    P008 --> P015[P0-15 学期/升级任务]
    P012 --> P015
    P014 --> P016[P0-16 冲突检测]
    P001 --> P017[P0-17 KP 分层字段]
    P017 --> P018[P0-18 四层种子]
    P018 --> P019[P0-19 单元/KP 接口]
    P019 --> P020[P0-20 学习状态机]
    P019 --> P021[P0-21 练习预览]
    P021 --> P022[P0-22 组卷扩展]
    P022 --> P023[P0-23 会话续答/结算]
    P023 --> P024[P0-24 提交扩展]
    P017 --> P025[P0-25 单元测蓝图]
    P022 --> P026[P0-26 试卷生成]
    P001 --> P027[P0-27 考试表]
    P026 --> P028[P0-28 考试接口]
    P027 --> P028
    P028 --> P029[P0-29 报告]
    P029 --> P030[P0-30 数据回流]
    P006 --> P031[P0-31 年级引导页]
    P008 --> P031
    P013 --> P031
    P003 --> P032[P0-32 守卫/权限 Gate]
    P014 --> P033[P0-33 学习首页]
    P013 --> P034[P0-34 教材管理]
    P019 --> P035[P0-35 知识树页]
    P021 --> P036[P0-36 练习页]
    P023 --> P036
    P028 --> P037[P0-37 考试页]
    P029 --> P037
    P031 --> P038[P0-38 前端测试]
    P037 --> P038
    P038 --> P041[P0-41 真机 E2E]
    P039[P0-39 后端单测] --> P040[P0-40 越权测试]
    P040 --> P041
    P041 --> P043[P0-43 里程碑验收]
```

```mermaid
flowchart LR
    R001[R-01 签名/版本号] --> R009[R-09 CI 与发布流水线]
    R002[R-02 生产部署] --> R003[R-03 隐私与同意链路]
    R003 --> R008[R-08 商店素材/合规表单]
    R001 --> R006[R-06 ICP/APP 备案]
    R003 --> R006
    R005[R-05 软著] --> R006
    P005[P0-05 审计日志] --> R004[R-04 注销/导出/家长同意]
    P009[P0-09 家长绑定] --> R004
    P018[P0-18 四层内容] --> R007[R-07 内容版权台账]
    R004 --> R006
    R007 --> R006
    R006 --> R008
```

> **发布关键路径**：R-01 → R-02 → R-03 → R-06（备案）→ R-08 → 提审；R-05 软著为最长外部周期，须第 1 天启动。R-04 依赖 P0-05/P0-09 完成后方可验收。

---

## 四、问题记录与解决方案

> 记录开发过程中的**技术难点、需求变更、阻塞问题、缺陷**；每条必须填写处理时间与结论。
> 状态：`OPEN` 待处理 / `RESOLVED` 已解决 / `MITIGATED` 已规避 / `DEFERRED` 延后。

### 4.1 问题台账

| ID | 日期 | 类型 | 描述 | 影响任务 | 严重度 | 处理人 | 解决方案 | 处理用时 | 状态 |
|---|---|---|---|---|---|---|---|---|---|
| I-001 | 2026-11-06 | 风险（数据） | 存量学生账号大量 `grade` 为空，直接强制必填会阻断登录 | P0-02/P0-31 | 高 | AR/PM | 采用"登录后强制引导 + 未完成仅开放公开浏览"的灰度策略；迁移仅回填学段不猜测年级 | P0-31 已落地 | `RESOLVED` |
| I-002 | 2026-11-06 | 风险（内容） | 部分知识点题量不足（<8 题），组卷 KP 覆盖 ≥80% 可能无法满足 | P0-22/P0-26 | 中 | CT/AR | 预览接口前置返回 `insufficient`；组卷按"同章→同学科→降难度"兜底；`test_practice_plan` 覆盖 ≥80% 与错题占比 ≤25% 用例通过 | P0-39/P0-43 已验证 | `RESOLVED` |
| I-003 | 2026-11-06 | 技术 | SQLite 对已有表加外键/约束需 `batch_alter_table`，否则迁移失败 | P0-01/P0-27 | 中 | AR | 已有 v0.3 经验，统一使用 batch 模式；迁移在空库与存量库各跑一次 | 已预置 | `MITIGATED` |
| I-004 | 2026-11-06 | 技术 | 断言 `autoflush=False` 下新对象默认值不落库，导致掌握度/错题为空 | P0-24/P0-30 | 中 | AR | 写操作显式 `db.flush()`；新对象显式赋默认值；补单测 | 已修复（v0.3） | `MITIGATED` |

### 4.2 需求变更记录（CR）

| CR ID | 日期 | 变更内容 | 提出人 | 影响范围 | 决策 | 决策人 | 关联任务 |
|---|---|---|---|---|---|---|---|
| — | — | 暂无 | — | — | — | — | — |

> 变更流程：提出 → 影响评估（任务/工时/验收） → PM 裁决 → 更新本表与任务台账 → 通知相关方。

### 4.3 阻塞记录

| 阻塞 ID | 日期 | 任务 | 阻塞原因 | 解除条件 | 责任人 | 预计解除 | 状态 |
|---|---|---|---|---|---|---|---|
| — | — | — | 暂无 | — | — | — | — |

---

## 五、进度快照与同步机制

### 5.1 当前进度快照（2026-11-06 开发启动后）

| 指标 | 数值 |
|---|---|
| 任务总数（不含基线） | 77（开发 68：P0 43 + P1 15 + P2 10；发布 9：R-01~R-09） |
| `TODO` | 25 |
| `DOING` | 0 |
| `DONE` | 52（P0-01~P0-43、P1-01~P1-09；基线 5 项已冻结） |
| `BLOCKED` | 0 |
| 预估总工时 | 676 h（开发 557 = P0 310 + P1 129 + P2 118；发布 119） |
| 已投入工时 | 165 h（P0-01 3、P0-02 2、P0-03 5、P0-04 4、P0-05 2、P0-06 2、P0-07 2、P0-08 3、P0-09 3、P0-10 3、P0-11 1、P0-12 2、P0-13 2、P0-14 2、P0-15 2、P0-16 1、P0-17 1、P0-18 2、P0-19 2、P0-20 2、P0-21 2、P0-22 3、P0-23 3、P0-24 3、P0-25 3、P0-26 3、P0-27 3、P0-28 4、P0-29 3、P0-30 3、P0-31 4、P0-32 3、P0-33 4、P0-34 4、P0-35 6、P0-36 8、P0-37 10、P0-38 4、P0-39 6、P0-40 4、P0-41 6、P0-42 2、P0-43 3、P1-01 3、P1-02 2、P1-03 2、P1-04 3、P1-05 3、P1-06 3、P1-07 3、P1-08 3、P1-09 3） |
| 当前迭代 | P1（角色扩展与综合考试）+ 发布准备（R-05 软著先行） |
| 迭代目标 | 教师/班主任/校管/家长角色可用；期中/期末/模考闭环；主观题自评与报告增强；推荐服务上线；并行推进软著/签名/隐私/部署 |
| 里程碑 | M2.5（P0 技术验收通过，待签署）→ M3（P1） |

### 5.2 同步节奏

| 频率 | 动作 | 责任人 | 产出 |
|---|---|---|---|
| 每次开发会话结束 | 更新任务状态、实际工时、证据；登记新问题 | 执行人（AR/FE/QA） | 本文件 §3/§4/§5.1 更新 |
| 每日 | 生成进度快照（完成数、阻塞数、偏差） | PM | §5.1 覆盖更新 + 会话汇报 |
| 每周 | 计划偏差评审：延期任务、优先级调整、风险复盘 | PM + 执行人 | §5.4 周报摘要 |
| 每个里程碑 | 验收签署、文档差异回写、基线冻结 | PM | 里程碑记录 + 设计文档更新 |

### 5.3 状态更新检查清单（每次会话结束自查）

- [ ] 所有 `DOING` 任务是否填写了实际工时与证据？
- [ ] 是否有任务满足 DoD 但未标记 `DONE`？
- [ ] `BLOCKED` 任务是否都在 §4.3 有记录且写了解除条件？
- [ ] 新发现的技术难点/需求变更是否进入 §4.1/§4.2？
- [ ] §5.1 快照数字是否与 §3 台账一致（总数、各状态数、工时）？
- [ ] 若完成里程碑，是否同步更新设计文档与验收记录？

### 5.4 周报摘要模板

```
周次：YYYY-Www
完成任务：P0-xx, P0-yy（附证据链接）
进行中：P0-zz（进度 xx%，剩余 xxh）
阻塞：I-xxx（原因 / 解除条件 / 责任人）
偏差：计划 xxh vs 实际 xxh（原因与纠偏）
风险：新增风险与应对
下周计划：任务清单
需 PM 决策：事项列表（若无写"无"）
```

### 5.5 更新记录（Changelog）

| 版本 | 日期 | 更新人 | 变更摘要 |
|---|---|---|---|
| v1.0 | 2026-11-06 | AR | 初始计划：拆分 P0/P1/P2 共 68 项任务；建立状态机制、问题台账、同步节奏；登记 4 条已知风险/经验 |
| v1.1 | 2026-11-06 | AR | 新增 §1.1 参考设计文档清单（D-01~D-07）与 §1.2 需求—设计—任务追踪矩阵，建立"需求→设计→任务→验收"双向追溯；补充文档优先级与状态规则；修正小节编号重复 |
| v1.2 | 2026-11-06 | AR | 文档清单新增 D-08 `release-plan.md`（发布方案，源稿）；同步更新文档数量（8 份）与优先级说明 |
| v1.3 | 2026-11-06 | AR | 新增 §3.4 发布与合规任务 R-01~R-09（119 h）与缺口→任务映射、发布验收 R-A1~R-A9、发布依赖图；新增 M5 发布就绪里程碑；总任务数 68→77，总工时 557→676 h |
| v1.4 | 2026-11-06 | AR | 开发启动：P0-01（users 年级维度 + grade_histories 迁移）、P0-02（年级派生与注册校验）标记 DONE 并补充证据；§5.1 快照同步（DONE 2 / 投入 5 h）；A1/A2 对应任务转 `DOING` |
| v1.5 | 2026-11-06 | AR | P0-03 权限底座落地（35 权限点 + 角色映射 + 范围映射 + `require_permission`/`require_admin`），标记 `DOING`（`require_student_access` 随 P0-04 完成）；§5.1 同步（DOING 1 / 投入 9 h） |
| v1.6 | 2026-11-06 | AR | P0-04 数据范围解析落地（SELF/CHILD/SCHOOL/ALL，CLASS 待 P1-01）、`users.school_id` 迁移 `e1b2c3d4f5a6`、`require_student_access` 完成，P0-03/P0-04 转 DONE；§5.1 同步（DONE 4 / 投入 14 h） |
| v1.7 | 2026-11-06 | AR | P0-05 审计服务落地（登录失败/停用/跨用户读取 + before/after）；P0-06 `/auth/me` 扩展与 `/auth/permissions` 上线；P0-05/P0-06 转 DONE；§5.1 同步（DONE 6 / 投入 18 h / pytest 50） |
| v1.8 | 2026-11-06 | AR | P0-07 JWT `ver` 与 `token_version` 校验落地（兼容旧 Token），`bump_token_version` 供角色/年级变更调用；A7 验收通过；§5.1 同步（DONE 7 / 投入 20 h / pytest 55） |
| v1.9 | 2026-11-06 | AR | P0-08 年级修改接口落地（428 二次确认令牌、每学期限 1 次、跨学段提示、历史与审计、Token 失效），旧 Token 401 统一返回 `TOKEN_REVOKED`；§5.1 同步（DONE 8 / 投入 23 h / pytest 62） |
| v1.10 | 2026-11-06 | AR | P0-09 家长绑定状态机落地（发起/确认/解除/我的孩子、`consent_at` 留痕、`/auth/me` 增加 `guardian_consent`）；§5.1 同步（DONE 9 / 投入 26 h / pytest 68） |
| v1.11 | 2026-11-06 | AR | P0-10 学习域范围改造落地（`stats`/`wrong-questions` 支持 `student_id`，多候选权限按角色范围择优，家长未选孩子 422）；§5.1 同步（DONE 10 / 投入 29 h / pytest 75） |
| v1.12 | 2026-11-06 | AR | P0-11 `textbook_bindings` 表与迁移 `f2b3c4d5e6a7` 落地；§5.1 同步（DONE 11 / 投入 30 h） |
| v1.13 | 2026-11-06 | AR | P0-12/P0-13 教材推荐、自动绑定与五个教材 API 落地（深圳版本优先、幂等 upsert、手动切换归档旧版本）；§5.1 同步（DONE 13 / 投入 34 h / pytest 82） |
| v1.14 | 2026-11-06 | AR | P0-14 学习首页聚合接口 `GET /api/learn/home` 落地（教材/今日计划/继续学习/推荐/待办考试，推荐优先级 复习→薄弱→专项→继续→每日一练），非学生 403；§1.2 学习首页转 `DOING`；§5.1 同步（DONE 14 / 投入 36 h / pytest 88） |
| v1.15 | 2026-11-06 | AR | P0-15 学期切换与学年升级任务落地（`switch_semester` 旧学期教材归档+新学期重绑；`promote_grades` 仅 9 月、按学年幂等、12 年级毕业、跨学段归档教材、历史+审计+Token 失效）；新增 cron 入口 `scripts/semester_jobs.py`；§6.1 A9 转 `DOING`；§5.1 同步（DONE 15 / 投入 38 h / pytest 93） |
| v1.16 | 2026-11-06 | AR | P0-16 教材与年级冲突检测落地（绑定/首页 `mismatch` 标记与 `mismatch_subjects` 告警、`/learn/start` 428 二次确认后放行）；§5.1 同步（DONE 16 / 投入 39 h / pytest 96） |
| v1.17 | 2026-11-06 | AR | P0-17 知识点四层结构落地（`node_type/order_index/weight` 三字段 + 迁移 `c3d4e5f6a7b8` 存量补"默认节"）；§1.2 知识点分层转 `DOING`；§5.1 同步（DONE 17 / 投入 40 h / pytest 98） |
| v1.18 | 2026-11-06 | AR | P0-18 内容种子四层改造（节/知识点挂接、同名误匹配修复、遗留"默认节"清理），全新库双跑种子稳定；§5.1 同步（DONE 18 / 投入 42 h / pytest 101） |
| v1.19 | 2026-11-06 | AR | P0-19 目录视图接口落地（教材单元列表、单元详情节聚合、知识点详情含前置与状态/最近学习时间）；§5.1 同步（DONE 19 / 投入 44 h / pytest 105） |
| v1.20 | 2026-11-06 | AR | P0-20 知识点学习状态机落地（`kp_study_states` 表 + 迁移、阅读/自测接口、提交自动写入、到期复习覆盖）；§5.1 同步（DONE 20 / 投入 46 h / pytest 108） |
| v1.21 | 2026-11-06 | AR | P0-21 练习组卷预览落地（四范围解析、确定性选题、到期错题配额、KP 覆盖率与时长统计，`POST /learn/practice/preview`）；修复分桶轮转在空桶时不推进游标导致的死循环；§1.2 智能辅助练习转 `DOING`；§6.1 L8 转 `DOING`；§5.1 同步（DONE 21 / 投入 48 h / pytest 113） |
| v1.22 | 2026-11-06 | AR | P0-22 组卷算法扩展落地（题型配比、KP 覆盖≥80%、7 天去重、时长预算、到期错题≤25%；`/learn/start` 与预览同 seed 同题并兼容旧参数）；§6.1 L6/L7、L8 转 `DOING`；§5.1 同步（DONE 22 / 投入 51 h / pytest 119） |
| v1.23 | 2026-11-06 | AR | P0-23 练习会话落地（`practice_sessions` 表 + 迁移 `e5f6a7b8c9d0`、`/start` 返回 `session_id`、断点续答 `GET /learn/sessions/{id}`、幂等结算 `POST .../finish` 含知识点表现与错题数）；§6.1 L13 转 `DOING`；§5.1 同步（DONE 23 / 投入 54 h / pytest 124） |
| v1.24 | 2026-11-06 | AR | P0-24 提交兼容扩展落地（答题记录 `source/session_id/kp_weight`、掌握度 `source_breakdown`、迁移 `f6a7b8c9d0e1`；`/learn/submit` 会话归属与来源校验；会话续答优先按 `session_id` 归属）；§6.1 L9~L12 转 `DOING`；§5.1 同步（DONE 24 / 投入 57 h / pytest 128） |
| v1.25 | 2026-11-06 | AR | P0-25 试卷蓝图落地（`exam_blueprints` 表 + 迁移 `g7b8c9d0e1f2`、小学语数英单元测种子、按 code 幂等写入）；§1.2 单元测试转 `DOING`；§5.1 同步（DONE 25 / 投入 60 h / pytest 131） |
| v1.26 | 2026-11-06 | AR | P0-26 试卷生成服务落地（蓝图分节 + 难度优先 + 知识点覆盖 + 跨节去重 + 题量兜底，seed 确定可复现）；§6.1 L9 推进；§5.1 同步（DONE 26 / 投入 63 h / pytest 136） |
| v1.27 | 2026-11-07 | AR | P0-27 考试表结构落地（`exams` 扩展 + `exam_attempts`/`exam_answers` + 迁移 `h8c9d0e1f2g3`，两级唯一约束与批改状态字段）；§6.1 L9~L12 推进；§5.1 同步（DONE 27 / 投入 66 h / pytest 140） |
| v1.28 | 2026-11-07 | AR | P0-28 考试接口落地（`GET /api/exams` 按年级/状态分类、详情不含答案、开始/续答（超时强制交卷后新建）、`PATCH` 幂等 upsert、`POST /submit` 按 `submit_token` 幂等且客观自动判/主观转 `grading`、`POST /generate` 按蓝图组卷）；§1.2 单元测试推进；§6.1 L9~L12 推进；§5.1 同步（DONE 28 / 投入 70 h / pytest 148） |
| v1.29 | 2026-11-07 | AR | P0-29 考试报告落地（`GET /api/exams/attempts/{id}/report`：未交卷 409、总分/正确率、题型得分率、知识点得分率、错题清单与解析、弱项/错题/再考下一步）；`tests/test_exam_report.py` 4 例；§6.1 L9~L12 推进；§5.1 同步（DONE 29 / 投入 73 h / pytest 152） |
| v1.30 | 2026-11-07 | AR | P0-30 考试数据回流落地（`student_question_records.attempt_id` + 迁移 `i9d0e1f2g3h4`；交卷客观题写答题记录/错题本/掌握度 EMA，权重单元测 0.8、期中 0.6、期末 0.5；主观题不回流；幂等不重复）；`tests/test_exam_backflow.py` 3 例；§6.1 L9~L12 推进；§5.1 同步（DONE 30 / 投入 76 h / pytest 155） |
| v1.31 | 2026-11-07 | AR | P0-31 年级引导页落地（教材绑定/推荐服务、年级变更 428 二次确认、`/gate` 判定与 `/onboarding` 三步引导、登录后进入 gate、路由守卫拦截）；§6.1 L1 转 `DONE`；§5.1 同步（DONE 31 / 投入 80 h / flutter test 8） |
| v1.32 | 2026-11-07 | AR | P0-32 路由守卫与权限错误引导落地（未登录统一跳 `/login`；`/shell`/`/home`/`/knowledge`/`/session`/`/practice` 由 `PermissionGate` 按权限点拦截；`ApiErrorGuide` 统一 401/403/业务码文案与重登/引导跳转；各页 catch 接入）；§6.1 A1/A2 转 `DONE`、A8 转 `DOING`；§5.1 同步（DONE 32 / 投入 83 h / flutter test 8） |
| v1.33 | 2026-11-07 | AR | P0-33 学习首页重构落地（`HomeData` 等首页聚合模型 + `learn_service.home()`；学生首页展示推荐下一步、今日计划、继续学习、学科入口教材卡与考试入口，儿童年级冲突标识；未绑定教材给推荐与 `/gate` 入口；非学生降级教材章节浏览）；`learn_model_test.dart` 新增 HomeData 2 例；§1.2 学习首页推进；§5.1 同步（DONE 33 / 投入 87 h / flutter test 10） |
| v1.34 | 2026-11-06 | AR | P0-34 教材管理页落地（学科 Chip + 上册/下册切换、版本选择与推荐标识、使用中高亮、年级不一致二次确认、解绑确认与空态；`textbook_service` 增加 `bind/unbind`、`api_client` 增加 `deleteJson`、新增 `/textbooks` 路由与首页/我的页入口）；后端 `manual_bind` 绑定学期以教材为准并跨学期归档同学科旧绑定；`tests/test_textbook.py` 新增 1 例；§1.2 教材绑定转 `DONE`、§6.1 L2/L3 转 `DONE`；§5.1 同步（DONE 34 / 投入 91 h / pytest 156 / flutter test 10） |
| v1.35 | 2026-11-06 | AR | P0-35 知识树与知识点详情落地（单元目录 → 节 → 知识点四层下钻；`unit_page` 展示节分组/状态/练一练/单元综合练习，`kp_detail_page` 展示讲解、前置跳转、掌握置信度、例题答案解析与「我已理解」；新增通用 `mastery_ring`；后端新增 `GET /learn/kp/{id}/examples` 带答案与解析）；§1.2 知识点分层转 `DONE`、§6.1 L4/L5 转 `DONE`；§5.1 同步（DONE 35 / 投入 97 h / pytest 157 / flutter test 10） |
| v1.36 | 2026-11-06 | AR | P0-36 智能练习前端落地（新增 `practice/config` 配置页：模式/范围/题量/题型 + 组卷预览；答题页扩展范围组卷、428 冲突二次确认、断点续答、提交带会话与来源、结算页含知识点表现与下一步；首页新增「继续上次练习」本地草稿入口）；§1.2 智能辅助练习转 `DONE`、§6.1 L8/L13 转 `DONE`；§5.1 同步（DONE 36 / 投入 105 h / pytest 157 / flutter test 10） |
| v1.37 | 2026-11-06 | AR | P0-37 考试前端闭环落地（新增考试中心列表、限时答题页（倒计时/答题卡/3 秒防抖自动保存/交卷确认/超时自动交卷）、报告页（总分/正确率、题型与知识点得分率、错题解析、薄弱点专项/错题重练/再考一次）；学习首页考试入口接通；`exam_model_test.dart` 3 例）；§1.2 单元测试转 `DONE`、§6.1 L9~L12 转 `DONE`；§5.1 同步（DONE 37 / 投入 115 h / pytest 157 / flutter test 13） |
| v1.38 | 2026-11-06 | AR | P0-38 前端单测补充（`PermissionGate` 权限守卫 5 例组件测试、`ApiErrorGuide` 错误映射 5 例、练习会话模型 4 例、教材绑定模型与学段映射 4 例）；§5.1 同步（DONE 38 / 投入 119 h / pytest 157 / flutter test 32） |
| v1.39 | 2026-11-06 | AR | P0-39 后端单测补充（年级派生全矩阵/越界码/选科/学年学期、9 角色权限矩阵与权限→范围映射、CLASS 安全空集与跨权限拒绝、考试守卫/超时结算/交卷只读/seed 冲突/报告权限与统计）；§5.1 同步（DONE 39 / 投入 125 h / pytest 203） |
| v1.40 | 2026-11-06 | AR | P0-40 越权专项测试（新增 `test_access_control.py`：跨学生统计/错题、教师跨班级、跨学校范围与接口拒绝、pending 绑定、家长越权、旧 Token 跨端点失效）；§6.1 L15 仍待 P0-41 端到端验收；§5.1 同步（DONE 40 / 投入 129 h / pytest 210） |
| v1.41 | 2026-11-06 | QA | P0-41 真机 E2E 通过（新增 `app/integration_test/learning_e2e_test.dart`，覆盖注册/登录→三步引导→首页→单元/知识点→练习配置与结算→错题本→考试中心→限时答题/交卷→报告→返回考试中心；`android/app/build.gradle.kts` 强制 espresso 3.5.1 修复 AGP 8 namespace 冲突；设备 `66B0219C18003002` 真机 E2E 全部通过）；§6.1 L15 转 `DONE`、A3~A6/A8 同步；§5.1 同步（DONE 41 / 投入 135 h） |
| v1.42 | 2026-11-06 | QA/AR | P0-42 迁移/种子回归（新增 `backend/tests/test_migrations.py`：空库 upgrade→downgrade→upgrade、存量库升级数据保留与回填、seed 双跑幂等；`ailearning_dev.db` 副本复核）；§6.1 A9 转 `DONE`；§5.1 同步（DONE 42 / 投入 137 h / pytest 213） |
| v1.43 | 2026-11-06 | PM | P0-43 P0 里程碑技术验收与文档同步（全量复核 `pytest` 213、`ruff` 0 issue、`flutter analyze` 0 issues、`flutter test` 32；§6.1 A10 转部分完成、L6/L7 转 `DONE`；§4.1 I-001/I-002 转 `RESOLVED`；§1.1 D-03/D-04 状态更新；新增 §6.2 验收记录；M2.5 技术验收通过待 PM 签署）；§5.1 同步（DONE 43 / 投入 140 h / TODO 34） |
| v1.44 | 2026-11-06 | AR | P1-01 学校/班级/成员/授课分配落地（`schools/classes/class_members/teacher_class_assignments` 四表与迁移 `j0e1f2g3h4i5`；CLASS 范围接入班主任全科可见与科任学科收窄、跨校/未绑定安全拒绝）；`tests/test_org.py` 4 例；§1.2 学校/教师组织能力转 `DOING`；§5.1 同步（DONE 44 / 投入 143 h / pytest 217） |
| v1.45 | 2026-11-07 | AR | P1-02 班级与授课分配 API 落地（`/org/schools`、`/org/classes`、`/org/classes/{id}/members`、`/org/assignments`；教师学科/年级范围与人班主任唯一性校验；批量入班幂等与跨校拒绝；审计四类操作；`tests/test_org_api.py` 3 例）；`require_any_permission` 依赖；§5.1 同步（DONE 45 / 投入 145 h / pytest 220） |
| v1.46 | 2026-11-07 | AR | P1-03 班级学情聚合接口（`GET /org/classes/{id}/stats` 仅返回聚合值：提交率/正确率/平均掌握度/薄弱 Top5；支持学科收窄，教师按授课班+学科、校管限本校；`tests/test_org_stats.py` 2 例）；§5.1 同步（DONE 46 / 投入 147 h / pytest 222） |
| v1.47 | 2026-11-07 | AR | P1-04 管理端用户列表与角色授予/回收（分页筛选+手机脱敏、校管限本校；自改/自授超管拒绝、Token 失效、审计 before/after；`tests/test_admin_users.py` 4 例）；§6.1 A10 更新（改角色审计已接入）；§5.1 同步（DONE 47 / 投入 150 h / pytest 226） |
| v1.48 | 2026-11-07 | AR | P1-05 家长端页面（后端 `teen_mode` 字段+迁移 `k1f2g3h4i5j6`、`PUT /family/children/{id}/controls` 含审计与边界校验、`tests/test_family_controls.py` 2 例；前端 `FamilyChild`/`FamilyService`/`ParentChildrenPage`（切换孩子、按 `student_id` 拉学情、每日时长、青少年模式）、`/family` 路由与个人中心入口、非学生隐藏个人统计；`flutter analyze` 0 issues、`flutter test` 38 passed、`pytest` 228 passed）；§1.2 家长绑定与未成年人合规转 `DONE`；§5.1 同步（DONE 48 / 投入 153 h / TODO 29） |
| v1.49 | 2026-11-07 | AR | P1-06 教师端页面（`ClassSummary`/`ClassStats` 模型与 `OrgService`、`TeacherClassesPage` 班级概览、`ClassStatsPage` 聚合报告与薄弱 Top5、`/teacher/classes` 路由与个人中心教师入口；`org_model_test.dart` 3 例、`teacher_pages_test.dart` 3 例；`flutter analyze` 0 issues、`flutter test` 44 passed）；§1.2 学校/教师组织能力转 `DONE`；§6.1 A3~A6 补充教师端；§5.1 同步（DONE 49 / 投入 156 h / TODO 28） |
| v1.50 | 2026-11-07 | AR | P1-07 期中/期末蓝图与组卷（6 套蓝图按 band 分带，得分 60/30/10、`kp_coverage_min=0.8`；`generate_paper` 支持 band→difficulty 映射；`tests/test_exam_comprehensive.py` 4 例验证两章范围组卷、难度得分配比、KP 覆盖、同 seed 幂等与 API 发布；`test_exam_blueprint.py` 同步 9 套断言；`pytest` 232 passed）；§1.2 期中/期末/模考转 `DOING`；§5.1 同步（DONE 50 / 投入 159 h / TODO 27） |
| v1.51 | 2026-11-07 | AR | P1-08 考试窗口与过期处理（`exams.window_start/window_end` + 迁移 `l2g3h4i5j6k7`；生成接口支持窗口、列表 `window_state`、窗口外开考 403、窗口关闭按已存答案自动交卷且拒收新答案，`tests/test_exam_window.py` 3 例；前端类型筛选与窗口展示/拦截，`exam_list_page_test.dart` 2 例；`pytest` 235 passed、`flutter test` 47 passed）；§5.1 同步（DONE 51 / 投入 162 h / TODO 26） |
| v1.52 | 2026-11-07 | AR | P1-09 主观题自评（报告 `pending_subjective` 含参考答案/评分点/解析、`POST /exams/attempts/{id}/self-assess` 成绩回写与首次回流、按卷重算主观/总分并转 completed，`tests/test_exam_self_assess.py` 4 例；前端自评卡与 `ExamService.selfAssess`，`exam_model_test.dart` +1 例、`exam_report_page_test.dart` 1 例；`pytest` 239 passed、`flutter analyze` 0 issues、`flutter test` 49 passed）；§1.2 主观题与报告增强转 `DOING`；§6.1 L9~L12 补充自评结算；§5.1 同步（DONE 52 / 投入 165 h / TODO 25） |

---

## 六、里程碑与验收台账

| 里程碑 | 包含任务 | 验收标准 | 计划状态 | 完成日期 | 验收人 |
|---|---|---|---|---|---|
| **M2.5（P0）** | P0-01 ~ P0-43 | 年级必填与引导可用；教材绑定生效；学习首页聚合；四层知识点可下钻；练习预览=实际、可续答；单元测可组卷/交卷/报告；错题与掌握度回流；权限越权测试全通过；真机 E2E 通过 | `DONE`（技术验收通过，待 PM 签署） | 2026-11-06 | PM（Agent 预验收） |
| **M3（P1）** | P1-01 ~ P1-15 | 教师/班主任/校管可用；家长端可用；期中/期末/模考闭环；主观题自评与报告增强；推荐服务上线 | `TODO` | — | PM |
| **M4（P2）** | P2-01 ~ P2-10 | RBAC 表与配置后台；教师作业；图谱；离线；AI 讲解；合规导出 | `TODO` | — | PM |
| **M5（发布就绪）** | R-01 ~ R-09 | 正式签名可验证；生产后端 HTTPS 可用；隐私 URL 与首启同意链路可用；注销/导出/家长同意/时长生效；软著受理；APP 备案下发；内容授权台账与免责声明上线；商店素材与表单齐备；发布流水线可追溯 | `TODO` | — | PM |

### 6.1 P0 验收对照（摘自设计文档）

| 编号 | 验收项 | 对应任务 | 状态 |
|---|---|---|---|
| A1/A2 | 年级必填 + 学段一致性 | P0-02/P0-08/P0-31 | `DONE`（后端校验 + 改年级 428 确认 + 前端三步引导） |
| A3~A6 | 越权拦截（学生/家长/教师/校管） | P0-04/P0-10/P0-40/P1-05/P1-06 | `DONE`（范围解析、家长端页面、教师端班级聚合页面、学习域改造 + `test_access_control.py` 越权用例通过） |
| A7 | 角色变更旧 Token 失效 | P0-07 | `DONE`（`ver` 校验 + `bump_token_version`） |
| A8 | 权限点覆盖所有路由 | P0-03/P0-32/P0-39 | `DONE`（前端路由守卫 + 后端 9 角色权限矩阵/权限→范围映射用例通过） |
| A9 | 升级幂等 | P0-01/P0-15/P0-42 | `DONE`（空库升级→降级→升级、存量库升级回填、seed 二次幂等回归全部通过） |
| A10 | 敏感操作审计 | P0-05/P1-04/P2-08 | `DOING`（登录失败/停用/注册/改年级/跨用户读取/家长绑定/学校班级成员/角色变更已审计；脱敏导出审计随 P2-08） |
| L1 | 3 步内完成年级+教材确认 | P0-31 | `DONE` |
| L2/L3 | 教材绑定幂等、上下册不混排 | P0-11~P0-13/P0-15/P0-16/P0-34 | `DONE`（服务端幂等/学期归档/冲突检测 + 前端教材管理页；手动绑定以教材学期为准并归档同学科旧绑定） |
| L4/L5 | 四层下钻、状态与掌握度 | P0-17~P0-20/P0-35 | `DONE`（服务端四层与状态机 + 前端单元目录/节/知识点详情、前置跳转与例题解析） |
| L6/L7 | 覆盖率≥80%、错题占比≤25% | P0-22/P0-39 | `DONE`（`test_practice_plan.py` 的 KP 覆盖 ≥80%、到期错题配额 ≤25% 用例通过） |
| L8 | 预览=实际（同 seed） | P0-21/P0-22/P0-36 | `DONE`（预览与 `/start` 同 seed 同题，前端配置页保留 seed 并直接开练） |
| L9~L12 | 组卷/交卷幂等/报告/数据回流 | P0-24~P0-30/P0-37/P0-39/P1-09 | `DONE`（服务端蓝图/试卷/交卷幂等/报告/数据回流 + 前端考试中心/限时答题/报告页已完成；主观题自评结算与回流由 P1-09 补齐，验收用例见 P0-39 与 P1-09） |
| L13 | 断点续答 | P0-23/P0-36 | `DONE`（会话按下一题下标续答，本地草稿入口与结算清理已完成） |
| L14 | 首页聚合 P95<300ms | P0-14/P1-13 | `TODO`（接口与前端首页已落地，性能待 P1-13 压测） |
| L15 | 权限范围与验收 | P0-10/P0-40/P0-41 | `DONE`（权限矩阵/范围/越权用例 + 真机 E2E 全链路验收通过） |

### 6.2 M2.5（P0）验收记录（2026-11-06）

| 核对项 | 结果 | 证据 |
|---|---|---|
| 任务台账 | P0-01~P0-43 共 43 项全部 `DONE`，无 `DOING`/`BLOCKED` | §3.1 |
| 后端回归 | `pytest` 213 passed；新增/修改文件 `ruff check` 0 issue | `backend/tests` |
| 前端回归 | `flutter analyze --no-pub` 0 issues；`flutter test --no-pub` 32 passed | `app/test` |
| 迁移/种子 | 空库升降级、存量库升级回填、seed 二次幂等全部通过 | `test_migrations.py`（P0-42） |
| 真机 E2E | 设备 `66B0219C18003002` 学习→练习→单元测→报告闭环通过 | `learning_e2e_test.dart`（P0-41） |
| 验收对照 | A1~A9、L1~L5、L6~L13、L15 `DONE`；A10 部分完成（导出审计随 P2-08）；L14 性能压测随 P1-13 | §6.1 |
| 设计文档差异 | P0 范围未发现需变更的设计偏差；D-03/D-04 的 P1/P2 章节仍待实施 | §1.1 |
| 遗留事项 | A10 导出审计随 P2-08、L14 P95 压测随 P1-13，不阻塞 M3 | — |

**结论**：M2.5 技术验收通过，待 PM（用户）签署后进入 P1。

---

## 七、开发执行约定

1. **分支与提交**：每个任务独立小步提交，提交信息含任务 ID（如 `P0-03: RBAC 权限依赖`）。
2. **迁移顺序**：先迁移后种子；迁移必须同时验证"空库升级"与"存量库升级"。
3. **接口兼容**：现有 `/api/learn/*` 与 `/api/practice/*` 保持兼容，新增参数可空、默认行为不变。
4. **权限先行**：涉及他人数据的接口必须先接入 `require_permission` + 范围解析，再实现业务查询。
5. **测试前置**：每个后端任务至少 1 个单测；每个前端页面至少 1 个模型/状态测试。
6. **文档同步**：实现与设计不一致时，先更新设计文档或登记 CR，再改代码。
7. **真机验证**：涉及页面的 P0 任务完成后，在 EBG 真机（`2NSDU20423005421`）走一遍主链路。
8. **计划更新**：每次会话结束按 §5.3 清单更新本文件，保持"台账-看板-快照"一致。

---

> **当前下一步**：P1-10（报告增强：能力维度雷达、班级平均、趋势对比）。所有任务按依赖图推进，每完成一个任务即回写本文件状态。
