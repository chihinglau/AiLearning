# 深爱学（AiLearning）用户角色定位及权限设计方案

> **文档性质**：专项设计方案（可落地实施蓝本）
> **版本**：v1.1（2026-11-12 按 CR-003 补考试域接口契约 §10.5、验收项 A11~A13 与权限点落地说明）
> **日期**：2026-11-06
> **最后更新**：2026-11-12（对应主计划 CR-003 / §6.22）
> **关联文档**：[k12-learning-app-design.md](./k12-learning-app-design.md)、[learning-page-design.md](./learning-page-design.md)、[subject-tutoring-and-m2-design.md](./subject-tutoring-and-m2-design.md)
> **适用范围**：学生 / 家长 / 教师 / 学校管理员 / 平台运营与审核

---

## 目录

1. [现状盘点与问题定义](#一现状盘点与问题定义)
2. [设计目标与原则](#二设计目标与原则)
3. [多级角色体系](#三多级角色体系)
4. [学生角色的年级维度细分](#四学生角色的年级维度细分)
5. [功能权限矩阵](#五功能权限矩阵)
6. [数据访问范围控制逻辑](#六数据访问范围控制逻辑)
7. [角色与年级关联的实现规则](#七角色与年级关联的实现规则)
8. [权限校验机制](#八权限校验机制)
9. [数据模型设计](#九数据模型设计)
10. [API 设计](#十api-设计)
11. [前端交互与年级选择](#十一前端交互与年级选择)
12. [实施计划与验收标准](#十二实施计划与验收标准)
13. [附录：权限点全量清单](#十三附录权限点全量清单)

---

## 一、现状盘点与问题定义

### 1.1 现状（代码事实）

| 位置 | 现状 | 影响 |
|---|---|---|
| `backend/app/models/user.py` | `role` 为字符串，取值 `student` / `parent` / `admin`；`stage`、`grade` 均可空 | 角色只有三层，无法表达教师、校管、运营、审计 |
| `backend/app/schemas/user.py` | 注册只允许 `student|parent`；`grade` 可选 1-12 | 学生可不选年级就进入学习流程 |
| `backend/app/api/deps.py` | 仅有 `get_current_user` 与 `require_admin` | 所有业务接口只校验"是否登录"，无功能级、数据级鉴权 |
| `backend/app/api/routes/learn.py` | 学情、错题、复习均按 `current.id` 查自己 | 家长看孩子、教师看班级无从实现；一旦放开查询参数即产生越权风险 |
| `app/lib/features/auth/login_page.dart` | 仅手机号 + 密码 | 无年级选择、无学生/家长身份分流 |
| `app/lib/features/profile/profile_page.dart` | 展示 `grade`，为 null 时显示"深圳学生" | 年级缺失被静默降级，学段内容策略无法生效 |

### 1.2 问题定义

1. **角色粒度过粗**：只有学生/家长/管理员，缺少教师、班主任、校级管理员、内容运营、审核员、客服、超级管理员。
2. **年级不是一等公民**：年级可空、可任意填，与学段不一致时无校验；年级变化无历史、无升级机制。
3. **没有数据范围（Data Scope）概念**：接口以"当前用户 id"硬编码，无法安全支撑家长/教师视角。
4. **权限是布尔判断**：`require_admin` 只能区分管理员/非管理员，新增角色必然改代码。
5. **前端缺失年级选择**：注册与首次登录都没有引导，导致教材、练习、考试范围全部依赖默认值。

### 1.3 设计边界

- 本方案覆盖 **C 端学习主链路 + 学校/平台管理侧**的角色与权限骨架。
- 一期不引入完整 OAuth/SSO、不引入 ABAC 规则引擎的可视化配置；采用 **RBAC + 属性约束（年级/学科/班级/学校）** 的混合模型。
- 支付、会员、广告等商业化权限不在本文展开，仅在权限点清单中预留命名空间。

---

## 二、设计目标与原则

### 2.1 目标

| 目标 | 可验证指标 |
|---|---|
| 角色可扩展 | 新增角色不改动业务路由代码，只增加角色-权限映射 |
| 年级可管控 | 学生账号 `grade` 非空率 100%；学段与年级一致性校验 100% 拦截 |
| 越权可防御 | 所有读接口带数据范围过滤；跨用户读取返回 403 且留痕 |
| 权限可审计 | 敏感操作（改角色、改年级、导出、查看他人学情）100% 写审计日志 |
| 体验无感 | 年级/教材确认 ≤ 3 步；权限不足时给出明确可执行提示 |

### 2.2 原则

1. **最小权限**：默认拒绝，显式授予。
2. **角色与数据范围分离**：角色决定"能做什么"，范围决定"能对谁做"。
3. **年级是属性不是角色**：不为每个年级建角色，避免角色爆炸（12 年级 × 多角色）。
4. **前后端双控、后端为准**：前端只做菜单/按钮显隐（UX），所有判定在后端完成。
5. **可演进**：一期保留 `users.role` 单角色兼容字段，二期切换为多角色表，读写双轨平滑迁移。
6. **合规优先**：未成年人数据、家长同意、儿童账号限制在权限层强制，而非仅靠产品约定。

---

## 三、多级角色体系

### 3.1 分层模型（四层）

```
┌──────────────────────────────────────────────────────────┐
│ L1 平台层   super_admin / content_operator / auditor      │
│             / customer_service                            │
├──────────────────────────────────────────────────────────┤
│ L2 机构层   school_admin / head_teacher / teacher         │
├──────────────────────────────────────────────────────────┤
│ L3 家庭层   parent(guardian)                              │
├──────────────────────────────────────────────────────────┤
│ L4 学习者   student（按学段/年级细分）                     │
├──────────────────────────────────────────────────────────┤
│ L0 匿名     guest                                         │
└──────────────────────────────────────────────────────────┘
```

### 3.2 角色定义表

| 角色编码 | 中文名 | 层级 | 核心职责 | 默认数据范围 |
|---|---|---|---|---|
| `guest` | 游客 | L0 | 浏览公开教材目录、试看题目 | `NONE`（仅公开内容） |
| `student` | 学生 | L4 | 学习、练习、考试、错题复习 | `SELF` |
| `parent` | 家长/监护人 | L3 | 查看孩子学情、设置时长与青少年模式、代管账号 | `CHILD`（已绑定且已同意） |
| `teacher` | 教师 | L2 | 布置作业/测验、查看所授班级学情、批改主观题 | `CLASS`（所授班级 + 所授学科） |
| `head_teacher` | 班主任 | L2 | 教师权限 + 本班全学科概览、学生名册 | `CLASS`（本班全学科） |
| `school_admin` | 校级管理员 | L2 | 班级/教师/学生名册管理、校级报表 | `SCHOOL` |
| `content_operator` | 内容运营 | L1 | 教材、章节、知识点、题库、试卷模板维护 | `ALL`（仅内容域） |
| `auditor` | 审核员 | L1 | 内容审核、合规审计只读 | `ALL`（只读，敏感字段脱敏） |
| `customer_service` | 客服 | L1 | 工单处理、账号问题协助 | `ALL`（用户资料脱敏只读） |
| `super_admin` | 超级管理员 | L1 | 角色分配、系统配置、全量数据 | `ALL` |

> 兼容映射：历史 `admin` → `super_admin`；历史 `student`/`parent` 不变。
> 学生不区分"小学/初中/高中"角色，而是通过 `stage + grade` 属性细分（见第四章）。

### 3.3 角色继承关系

采用"基础角色 + 附加角色"的组合，而非无限继承链：

```
student ──────────────┐
parent  ──────────────┼──► 基础能力（学习域只读/自管）
teacher ──► head_teacher（增加本班全科概览）
        └─► school_admin（增加名册与校级报表）
content_operator ──► super_admin（增加用户与角色管理）
auditor / customer_service 为独立只读角色，不继承写权限
```

规则：

- 一个用户可有 **1 个主角色 + N 个附加角色**（如教师兼任班主任、家长同时是教师）。
- 权限取并集，数据范围取**最宽且合法**的并集（例如教师 + 家长：既是 CLASS 也是 CHILD）。
- 主角色决定默认首页与导航结构。

---

## 四、学生角色的年级维度细分

### 4.1 学段与年级映射（唯一事实来源）

| 学段 `stage` | 年级 `grade` | 学段分组 `grade_group` | 说明 |
|---|---|---|---|
| `primary` 小学 | 1-2 | `primary_low` 低段 | 拼音、识字、口算、英语启蒙 |
| `primary` 小学 | 3-4 | `primary_mid` 中段 | 阅读、应用题、书写规范 |
| `primary` 小学 | 5-6 | `primary_high` 高段 | 小升初衔接、综合复习 |
| `junior` 初中 | 7-9 | `junior` 初中 | 中考、理化生开课、错题体系 |
| `senior` 高中 | 10-12 | `senior` 高中 | 选科、模考、真题 |

派生函数（服务端唯一实现，禁止前端自行计算）：

```python
def derive_stage(grade: int) -> str:
    if 1 <= grade <= 6:  return "primary"
    if 7 <= grade <= 9:  return "junior"
    if 10 <= grade <= 12: return "senior"
    raise ValueError("grade 必须在 1-12")

def derive_grade_group(grade: int) -> str:
    if grade <= 2:  return "primary_low"
    if grade <= 4:  return "primary_mid"
    if grade <= 6:  return "primary_high"
    if grade <= 9:  return "junior"
    return "senior"
```

### 4.2 年级维度对产品的影响

| 维度 | 小学低段 1-2 | 小学中高段 3-6 | 初中 7-9 | 高中 10-12 |
|---|---|---|---|---|
| 默认单次练习题量 | 6-10 题 | 10-15 题 | 15-20 题 | 15-25 题 |
| 单次时长上限 | 10-15 分钟 | 20 分钟 | 30 分钟 | 45 分钟 |
| 每日时长管控 | 严格（默认 40 分钟） | 默认 60 分钟 | 默认 90 分钟 | 默认 120 分钟 |
| 题型重心 | 选择/判断/填空/口算 | + 阅读理解、应用题 | + 实验探究、材料分析 | + 多选、计算大题、写作 |
| 练习反馈 | 即时反馈 + 语音鼓励 | 即时反馈 | 即时反馈（可切换延后） | 延后反馈（模拟考试） |
| 考试体系 | 单元测（游戏化） | 单元测 + 期中/期末 | + 中考模拟 | + 高考模拟/选科 |
| 教材绑定 | 语文/数学/英语 | 语文/数学/英语 | + 物理/化学/生物/史地政 | + 选科组合 |
| 家长可见 | 全量 + 陪伴提示 | 全量 | 全量（尊重隐私可配置） | 成绩与规划为主 |

### 4.3 年级相关属性

| 字段 | 类型 | 说明 | 约束 |
|---|---|---|---|
| `grade` | int | 当前年级 1-12 | 学生必填；写入时派生 `stage` |
| `stage` | enum | 派生字段 | 只读，服务端写入 |
| `grade_group` | enum | 派生字段 | 只读，服务端写入 |
| `enrollment_year` | int | 入学年份（用于升级计算） | 可空，首次确认年级时写入 |
| `region` | string | 默认 `shenzhen` | 影响教材版本推荐 |
| `semester` | enum | `first` / `second` | 按日期派生，可手动切换 |
| `elective_subjects` | JSON | 高中选科组合（3+1+2） | 仅 grade 10-12 可写 |
| `grade_updated_at` | datetime | 最近一次年级变更时间 | 审计用 |
| `graduated_at` | datetime | 高三毕业时间 | 非空即转为校友只读 |

### 4.4 年级变更与升级规则

| 场景 | 触发方式 | 处理 |
|---|---|---|
| 首次确认年级 | 注册/首次登录引导 | 学生必选；写 `enrollment_year`、重算教材绑定 |
| 学期切换 | 系统定时（2 月/9 月）或手动 | 切换 `semester`，教材绑定按新学期重算 |
| 学年升级 | 每年 9 月 1 日定时任务 | `grade + 1`；12 年级 → `graduated_at`；写历史表 |
| 手动改年级 | 用户在"我的-年级"修改 | 每学期限 1 次；需二次确认；影响范围提示；写审计 |
| 教师/校管修正 | 管理端 | 可越过频率限制，必须填写原因并留痕 |
| 跨学段变更 | 6→7、9→10 | 强制重新确认教材版本与学科列表 |
| 年级与教材冲突 | 绑定的教材 `grade != user.grade` | 标记 `mismatch`，学习页提示并可一键重绑 |

**升级幂等**：定时任务以 `(user_id, target_grade, school_year)` 唯一键写入 `grade_histories`，重复执行不重复升级。

---

## 五、功能权限矩阵

### 5.1 符号约定

- ✅ 完整可用
- 🔶 受限可用（受数据范围/状态约束，如仅本人、仅绑定孩子、仅所授班级）
- 👁 只读
- ❌ 禁止

### 5.2 学习域

| 功能 / 权限点 | 游客 | 学生 | 家长 | 教师 | 班主任 | 校管 | 内容运营 | 审核 | 客服 | 超管 |
|---|---|---|---|---|---|---|---|---|---|---|
| 浏览公开教材目录 `learn:content:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 👁 | 👁 | ✅ |
| 进入知识点学习 `learn:kp:study` | ❌ | 🔶自 | ❌ | 👁班 | 👁班 | 👁校 | 👁 | 👁 | ❌ | ✅ |
| 开始自适应练习 `learn:practice:start` | ❌ | 🔶自 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 提交作答 `learn:practice:submit` | ❌ | 🔶自 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 查看本人学情 `learn:stats:self:read` | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 查看孩子学情 `learn:stats:child:read` | ❌ | ❌ | 🔶绑定 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 查看班级学情 `learn:stats:class:read` | ❌ | ❌ | ❌ | 🔶所授 | 🔶本班 | 🔶本校 | ❌ | ❌ | ❌ | ✅ |
| 错题本（本人）`learn:wrong:self` | ❌ | ✅ | 👁孩子 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 标注错因 `learn:wrong:annotate` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 今日复习 `learn:review:today` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 参加考试 `learn:exam:take` | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 查看本人考试报告 `learn:exam:report:self` | ❌ | ✅ | 🔶孩子 | 👁班 | 👁班 | 👁校 | ❌ | 👁 | ❌ | ✅ |
| 布置作业/测验 `learn:assignment:create` | ❌ | ❌ | ❌ | 🔶所授 | 🔶本班 | 🔶本校 | ❌ | ❌ | ❌ | ✅ |
| 批改主观题 `learn:exam:grade` | ❌ | ❌ | ❌ | 🔶所授 | 🔶本班 | ❌ | ❌ | ❌ | ❌ | ✅ |

### 5.3 内容域

| 功能 / 权限点 | 游客 | 学生 | 家长 | 教师 | 班主任 | 校管 | 内容运营 | 审核 | 客服 | 超管 |
|---|---|---|---|---|---|---|---|---|---|---|
| 维护教材/章节 `content:textbook:write` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | 👁 | ❌ | ✅ |
| 维护知识点 `content:kp:write` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | 👁 | ❌ | ✅ |
| 维护题库/题目 `content:question:write` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | 👁 | ❌ | ✅ |
| 发布试卷模板 `content:exam:write` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | 👁 | ❌ | ✅ |
| 内容审核/驳回 `content:review:decide` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 👁 | ✅ | ❌ | ✅ |
| 内容上下架 `content:publish` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |

### 5.4 家庭域

| 功能 / 权限点 | 游客 | 学生 | 家长 | 教师 | 班主任 | 校管 | 内容运营 | 审核 | 客服 | 超管 |
|---|---|---|---|---|---|---|---|---|---|---|
| 发起家长绑定 `family:binding:request` | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 确认/解除绑定 `family:binding:manage` | ❌ | 🔶确认 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 设置孩子时长/青少年模式 `family:control:write` | ❌ | ❌ | 🔶绑定 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 查看孩子学习报告 `family:report:read` | ❌ | ❌ | 🔶绑定 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

### 5.5 组织与平台域

| 功能 / 权限点 | 游客 | 学生 | 家长 | 教师 | 班主任 | 校管 | 内容运营 | 审核 | 客服 | 超管 |
|---|---|---|---|---|---|---|---|---|---|---|
| 班级管理 `org:class:manage` | ❌ | ❌ | ❌ | ❌ | 👁 | ✅ | ❌ | ❌ | ❌ | ✅ |
| 学生名册 `org:student:manage` | ❌ | ❌ | ❌ | 👁班 | 👁班 | ✅ | ❌ | ❌ | 👁脱敏 | ✅ |
| 教师分配 `org:teacher:assign` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| 用户管理 `admin:user:manage` | ❌ | ❌ | ❌ | ❌ | ❌ | 🔶本校 | ❌ | 👁 | 👁脱敏 | ✅ |
| 角色分配 `admin:role:assign` | ❌ | ❌ | ❌ | ❌ | ❌ | 🔶本校非管理员 | ❌ | ❌ | ❌ | ✅ |
| 审计日志 `audit:log:read` | ❌ | ❌ | ❌ | ❌ | ❌ | 👁本校 | ❌ | ✅ | ❌ | ✅ |
| 客服工单 `support:ticket:manage` | ❌ | ✅提交 | ✅提交 | ✅提交 | ✅提交 | ✅提交 | ❌ | ❌ | ✅ | ✅ |
| 系统配置 `system:config:write` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

> 完整权限点编码清单见[第十三章](#十三附录权限点全量清单)。

---

## 六、数据访问范围控制逻辑

### 6.1 范围类型

| 范围 | 编码 | 解析结果 | 适用角色 |
|---|---|---|---|
| 无 | `NONE` | 空集（仅公开内容） | 游客 |
| 本人 | `SELF` | `{current_user_id}` | 学生、教师（自身） |
| 绑定子女 | `CHILD` | `parent_child_bindings` 中 `parent_id=me AND status=active` 的 `child_id` 集合 | 家长 |
| 所授班级 | `CLASS` | `teacher_class_assignments` 中 `teacher_id=me` 的 `class_id`，可再按 `subject` 收窄 | 教师 |
| 本班 | `CLASS`（全科） | 班主任的 `class_id` | 班主任 |
| 本校 | `SCHOOL` | `users.school_id = me.school_id` | 校管 |
| 全部 | `ALL` | 无过滤（内容域/平台域） | 运营、审核、超管 |

### 6.2 解析优先级

多角色用户按"请求所需权限"选择对应范围，不盲目取并集：

```
请求 (permission, target_id?)
  ├─ 解析角色 → 找到拥有该权限的角色集合
  ├─ 对每个角色解析其数据范围 → 得到候选目标集合 S1…Sn
  ├─ 若 target_id 存在：判断 target_id ∈ (S1 ∪ … ∪ Sn)，否则 403 SCOPE_DENIED
  └─ 若 target_id 不存在：查询时用 (S1 ∪ … ∪ Sn) 作为 WHERE 条件
```

示例：家长同时是教师，请求 `learn:stats:class:read` 时只使用 CLASS 范围；请求 `learn:stats:child:read` 时只使用 CHILD 范围，互不交叉提权。

### 6.3 范围过滤实现（服务层统一入口）

```python
# backend/app/core/scope.py
Scope = Literal["NONE", "SELF", "CHILD", "CLASS", "SCHOOL", "ALL"]

def resolve_student_ids(db: Session, actor: User, scope: Scope, subject: str | None = None) -> set[int] | None:
    """返回允许访问的 student_id 集合；None 表示不限制（ALL）。"""
    if scope == "ALL":
        return None
    if scope == "SELF":
        return {actor.id}
    if scope == "CHILD":
        rows = db.scalars(
            select(ParentChildBinding.child_id).where(
                ParentChildBinding.parent_id == actor.id,
                ParentChildBinding.status == "active",
            )
        )
        return set(rows)
    if scope == "CLASS":
        q = select(ClassMember.student_id).join(
            TeacherClassAssignment,
            TeacherClassAssignment.class_id == ClassMember.class_id,
        ).where(TeacherClassAssignment.teacher_id == actor.id)
        if subject:
            q = q.where(TeacherClassAssignment.subject == subject)
        return set(db.scalars(q))
    if scope == "SCHOOL":
        return set(db.scalars(
            select(User.id).where(User.school_id == actor.school_id, User.role == "student")
        ))
    return set()
```

业务查询统一写法：

```python
allowed = resolve_student_ids(db, current, scope)
stmt = select(WrongQuestion).where(WrongQuestion.user_id == student_id)
if allowed is not None and student_id not in allowed:
    raise HTTPException(403, detail={"code": "SCOPE_DENIED", "message": "无权访问该学生数据"})
```

### 6.4 写操作的归属校验

| 写操作 | 校验规则 |
|---|---|
| 提交作答 / 标注错因 / 复习 | `question_record.user_id == current.id`（学生只能写自己的） |
| 家长设置时长 | 目标 child 必须在 active 绑定集合内 |
| 教师布置作业 | `class_id ∈ 所授班级` 且 `subject ∈ 所授学科` |
| 校管改学生年级 | `student.school_id == admin.school_id` |
| 运营改题目 | 需 `content:question:write` + 内容状态不是 `published`（已发布需走审核流） |

### 6.5 聚合与脱敏

- 教师查看班级学情：只返回**聚合值**（平均掌握度、薄弱点 TopN、提交率），不返回其他学生逐题作答原文。
- 客服/审核查看用户：手机号中间四位掩码、昵称可读、学习明细不可读。
- 家长查看孩子：可读学情与错题，不可读孩子与同伴的对比排名（合规要求）。

### 6.6 越权响应规范

| 场景 | HTTP | 业务码 | 文案 |
|---|---|---|---|
| 未登录/Token 失效 | 401 | `UNAUTHENTICATED` | 登录状态已失效，请重新登录 |
| 已登录但无该功能 | 403 | `PERMISSION_DENIED` | 当前账号无此功能权限 |
| 有功能但目标不在范围 | 403 | `SCOPE_DENIED` | 无权访问该数据 |
| 年级不匹配（如用 3 年级教材做 5 年级考试） | 409 | `GRADE_MISMATCH` | 当前年级与内容不匹配，请切换教材 |
| 儿童账号未获家长同意 | 403 | `CONSENT_REQUIRED` | 需家长确认后使用 |

---

## 七、角色与年级关联的实现规则

### 7.1 学生

| 规则 | 实现 |
|---|---|
| 年级必填 | 注册时 `role=student` 则 `grade` 必填；缺失返回 422 `GRADE_REQUIRED` |
| 学段派生 | 服务端由 `grade` 计算 `stage/grade_group`，忽略客户端传值 |
| 一致性 | 请求携带 `stage` 与派生值不符 → 422 `STAGE_MISMATCH` |
| 首次引导 | 已有账号 `grade is null` 时，登录后强制跳转 `/on-grade`，未完成不可进入学习页 |
| 修改频率 | 学生自助每学期 1 次；以 `grade_histories` 统计 |
| 变更影响 | 触发：教材重绑提示、考试范围重算、推荐策略刷新；历史学情保留并标注"X 年级" |
| 毕业 | `grade=12` 且到毕业时间 → `graduated_at` 写入，转为只读校友（可查看历史） |

### 7.2 家长

| 规则 | 实现 |
|---|---|
| 绑定关系 | `ParentChildBinding(parent_id, child_id, relation, status, consent_at)`，唯一键 `(parent_id, child_id)` |
| 状态机 | `pending`（家长发起）→ `active`（孩子/监护人确认）→ `revoked`（任一方解除） |
| 数据范围 | 仅 `active` 绑定；`pending` 不可读任何数据 |
| 多孩子 | 允许 1:N；前端提供"当前孩子"切换，接口显式传 `child_id` |
| 儿童账号 | `is_child=true` 的账号需至少 1 个 active 家长绑定 + `consent_at` 非空，否则限制社交/分享/付费 |
| 年级可见 | 家长可读孩子年级，不可直接修改（需孩子确认或校管修正） |

### 7.3 教师 / 班主任

| 规则 | 实现 |
|---|---|
| 学科范围 | `teacher_subjects`（JSON 数组，如 `["math"]`） |
| 年级范围 | `grade_start`、`grade_end`（如 7-9），布置作业/考试时校验目标年级落在此区间 |
| 班级范围 | `teacher_class_assignments(teacher_id, class_id, subject, role_in_class)` |
| 班主任 | `role_in_class=head_teacher`，额外获得本班全学科概览 |
| 跨校 | 不允许；`teacher.school_id` 必须与班级 `school_id` 一致 |

### 7.4 校管 / 内容运营 / 审核 / 客服

| 角色 | 关联规则 |
|---|---|
| `school_admin` | 必须绑定 `school_id`；只能管理本校用户；不能给自己授予 `super_admin` |
| `content_operator` | 绑定 `subject_scope`（可空=全学科）与 `grade_scope`（可空=全年级）；只影响内容域权限 |
| `auditor` | 无年级概念；只读内容与审计日志；用户数据脱敏 |
| `customer_service` | 无年级概念；只读脱敏用户资料；可写工单 |

### 7.5 角色-年级一致性校验表

| 校验 | 触发点 | 失败处理 |
|---|---|---|
| student 必须有 grade | 注册、资料更新、登录后引导 | 422 / 强制引导页 |
| stage 必须等于 derive(grade) | 注册、更新、管理端修改 | 422，服务端覆盖为派生值 |
| grade 10-12 才能写选科 | 更新选科 | 409 `GRADE_MISMATCH` |
| teacher 的 grade_scope 必须覆盖所授班级年级 | 班级分配 | 409，拒绝分配 |
| parent 不能绑定非 student 账号 | 绑定 | 422 |
| 校管只能操作本校用户 | 任意管理写操作 | 403 `SCOPE_DENIED` |
| 12 年级不得再升级 | 升级任务 | 写 `graduated_at`，不越界 |

---

## 八、权限校验机制

### 8.1 认证（Authentication）

**JWT 载荷**：

```json
{
  "sub": "1001",
  "role": "student",
  "grade": 3,
  "ver": 7,
  "exp": 1765000000
}
```

- `ver` 对应用户 `token_version`；角色、年级、绑定关系变更时 `token_version += 1`，旧 Token 立即失效。
- 有效期 24h；刷新采用重新登录（一期不做 refresh token，降低复杂度）。
- `get_current_user` 增加 `ver` 比对；不匹配返回 401 `TOKEN_REVOKED`。

### 8.2 授权链（Authorization Pipeline）

```
HTTP 请求
  → OAuth2 Bearer 解析
  → get_current_user（校验 Token、ver、is_active）
  → require_permission("learn:practice:start")
        ├─ 角色 → 权限点集合（含继承）
        └─ 无权限 → 403 PERMISSION_DENIED
  → resolve_scope（根据权限点绑定的范围类型）
  → service 层查询/写入时应用 scope 过滤
  → 写操作 → AuditLog
  → 响应
```

### 8.3 后端实现骨架

**权限注册表**（声明式，新增角色只改数据/映射）：

```python
# backend/app/core/rbac.py
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "guest": {"learn:content:read"},
    "student": {
        "learn:content:read", "learn:kp:study", "learn:practice:start",
        "learn:practice:submit", "learn:stats:self:read", "learn:wrong:self",
        "learn:wrong:annotate", "learn:review:today", "learn:exam:take",
        "learn:exam:report:self", "user:profile:update", "support:ticket:manage",
    },
    "parent": {...},
    "teacher": {...},
    "head_teacher": {...} | {"learn:stats:class:read"},
    "school_admin": {...},
    "content_operator": {...},
    "auditor": {...},
    "customer_service": {...},
    "super_admin": {"*"},
}

PERMISSION_SCOPE: dict[str, str] = {
    "learn:stats:self:read": "SELF",
    "learn:stats:child:read": "CHILD",
    "learn:stats:class:read": "CLASS",
    "learn:exam:report:self": "SELF",
    "learn:assignment:create": "CLASS",
    "content:textbook:write": "ALL",
    ...
}
```

**依赖注入**：

```python
def require_permission(code: str):
    def dependency(current: User = Depends(get_current_user)) -> User:
        if not has_permission(current, code):
            raise HTTPException(403, detail={"code": "PERMISSION_DENIED", "message": "当前账号无此功能权限"})
        return current
    return dependency

# 路由使用
@router.post("/learn/start")
def start(..., current: User = Depends(require_permission("learn:practice:start"))):
    ...
```

**范围依赖**（需要指定目标学生时）：

```python
def require_student_access(permission_code: str):
    def dependency(student_id: int, current: User = Depends(require_permission(permission_code)),
                   db: Session = Depends(get_db)) -> int:
        scope = PERMISSION_SCOPE[permission_code]
        allowed = resolve_student_ids(db, current, scope)
        if allowed is not None and student_id not in allowed:
            raise HTTPException(403, detail={"code": "SCOPE_DENIED", "message": "无权访问该学生数据"})
        return student_id
    return dependency
```

**兼容旧接口**：`require_admin` 内部改为 `has_permission(current, "*")` 或 `role in {"super_admin"}`，避免新旧两套并行。

### 8.4 前端权限态

| 层 | 做法 |
|---|---|
| 路由守卫 | 登录后拉取 `/auth/me` 与 `/auth/permissions`，未完成年级引导则跳 `/on-grade` |
| 菜单/按钮 | `PermissionGate(permission: "learn:exam:take")`，无权限时不渲染或禁用并给出原因 |
| 数据范围切换 | 家长端顶部"当前孩子"切换；教师端"当前班级/学科"切换，切换后所有查询显式带 `child_id/class_id` |
| 错误处理 | 统一拦截 403，按 `code` 展示可执行引导（如"去绑定孩子""切换班级"） |
| 安全边界 | 前端隐藏仅为体验优化；任何敏感操作仍以服务端返回为准 |

### 8.5 审计与安全增强

| 操作 | 审计 action | 附加要求 |
|---|---|---|
| 登录失败 | `auth.login_failed` | 记录 IP、手机号掩码，5 次/10 分钟限流 |
| 角色变更 | `admin.role.assign` | 记录 before/after、操作人；不可自授超管 |
| 年级变更 | `user.grade.change` | 记录 before/after、来源（自助/校管/升级任务） |
| 查看他人学情 | `learn.stats.cross_read` | 记录目标 student_id（家长/教师高频，采样记录） |
| 导出数据 | `data.export` | 记录范围、条数、用途 |
| 内容发布 | `content.publish` | 双人复核（运营 + 审核） |

**防越权红线**：

1. 任何接口不得接受客户端传入的 `role` 并据此提权。
2. 角色判定只读服务端用户表/角色表，不读 JWT 中的 role 作为唯一依据（JWT 仅作快速拒绝）。
3. 批量接口必须逐个目标做范围校验，禁止"先查后滤"导致信息泄露（如计数、排序侧信道）。
4. 列表接口默认分页，禁止 `limit` 无上限。

---

## 九、数据模型设计

### 9.1 新增/扩展表

```sql
-- 1) users 扩展（保留 role 兼容字段）
ALTER TABLE users ADD COLUMN school_id     BIGINT NULL;
ALTER TABLE users ADD COLUMN enrollment_year INT NULL;
ALTER TABLE users ADD COLUMN region        VARCHAR(20) DEFAULT 'shenzhen';
ALTER TABLE users ADD COLUMN grade_group   VARCHAR(20) NULL;      -- 派生
ALTER TABLE users ADD COLUMN semester      VARCHAR(10) DEFAULT 'first';
ALTER TABLE users ADD COLUMN elective_subjects JSON NULL;          -- 高中选科
ALTER TABLE users ADD COLUMN grade_updated_at DATETIME NULL;
ALTER TABLE users ADD COLUMN graduated_at  DATETIME NULL;
ALTER TABLE users ADD COLUMN token_version INT DEFAULT 0;
ALTER TABLE users ADD COLUMN teacher_subjects JSON NULL;
ALTER TABLE users ADD COLUMN grade_start   INT NULL;               -- 教师可授年级
ALTER TABLE users ADD COLUMN grade_end     INT NULL;

-- 2) 角色与权限（二期启用，一期可用常量映射）
CREATE TABLE roles (
  id BIGINT PRIMARY KEY,
  code VARCHAR(40) UNIQUE NOT NULL,
  name VARCHAR(60) NOT NULL,
  level VARCHAR(10) NOT NULL,          -- L0-L4
  is_system BOOLEAN DEFAULT TRUE
);

CREATE TABLE permissions (
  id BIGINT PRIMARY KEY,
  code VARCHAR(80) UNIQUE NOT NULL,    -- domain:resource:action
  domain VARCHAR(20) NOT NULL,
  description VARCHAR(200)
);

CREATE TABLE role_permissions (
  role_id BIGINT NOT NULL,
  permission_id BIGINT NOT NULL,
  PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE user_roles (
  user_id BIGINT NOT NULL,
  role_id BIGINT NOT NULL,
  is_primary BOOLEAN DEFAULT FALSE,
  granted_by BIGINT NULL,
  granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, role_id)
);

-- 3) 学校 / 班级 / 成员 / 授课
CREATE TABLE schools (
  id BIGINT PRIMARY KEY, name VARCHAR(120), region VARCHAR(20) DEFAULT 'shenzhen'
);

CREATE TABLE classes (
  id BIGINT PRIMARY KEY,
  school_id BIGINT NOT NULL,
  grade INT NOT NULL,
  name VARCHAR(60) NOT NULL,
  head_teacher_id BIGINT NULL,
  school_year VARCHAR(20) NOT NULL
);

CREATE TABLE class_members (
  class_id BIGINT NOT NULL,
  student_id BIGINT NOT NULL,
  joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (class_id, student_id)
);

CREATE TABLE teacher_class_assignments (
  id BIGINT PRIMARY KEY,
  teacher_id BIGINT NOT NULL,
  class_id BIGINT NOT NULL,
  subject VARCHAR(20) NOT NULL,
  role_in_class VARCHAR(20) DEFAULT 'subject_teacher',  -- subject_teacher|head_teacher
  UNIQUE (teacher_id, class_id, subject)
);

-- 4) 年级历史（升级与审计）
CREATE TABLE grade_histories (
  id BIGINT PRIMARY KEY,
  user_id BIGINT NOT NULL,
  from_grade INT NULL,
  to_grade INT NOT NULL,
  school_year VARCHAR(20) NOT NULL,
  source VARCHAR(20) NOT NULL,         -- onboarding|self|admin|promotion
  reason VARCHAR(200) NULL,
  operator_id BIGINT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (user_id, to_grade, school_year)
);
```

### 9.2 兼容与迁移策略

| 阶段 | 内容 | 风险控制 |
|---|---|---|
| A（与现有代码兼容） | 加列、加表；`role` 字符串继续读写；`admin` 映射 `super_admin`；常量权限映射上线 | 所有新列可空/有默认值，存量用户不受影响 |
| B（双写） | 新注册/角色变更同时写 `user_roles`；读取优先 `user_roles`，回退 `users.role` | 差异对账任务每日核对 |
| C（切换） | 全部读 `user_roles`；`users.role` 降级为主角色缓存 | 保留回滚开关 |
| D（清理） | 删除兼容逻辑（至少 2 个版本后） | — |

**存量数据回填**：

```sql
UPDATE users SET stage = CASE
  WHEN grade BETWEEN 1 AND 6 THEN 'primary'
  WHEN grade BETWEEN 7 AND 9 THEN 'junior'
  WHEN grade BETWEEN 10 AND 12 THEN 'senior'
  ELSE NULL END
WHERE role = 'student' AND grade IS NOT NULL;

UPDATE users SET grade_group = CASE
  WHEN grade <= 2 THEN 'primary_low' WHEN grade <= 4 THEN 'primary_mid'
  WHEN grade <= 6 THEN 'primary_high' WHEN grade <= 9 THEN 'junior'
  ELSE 'senior' END
WHERE grade IS NOT NULL;
```

---

## 十、API 设计

### 10.1 账号与年级

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/api/auth/register` | 公开 | 学生 `grade` 必填；服务端派生 `stage/grade_group` |
| GET | `/api/auth/me` | 登录 | 返回 `role/stage/grade/grade_group/semester/permissions` |
| GET | `/api/auth/permissions` | 登录 | 当前用户权限点集合 + 范围类型（供前端显隐） |
| PUT | `/api/users/me/grade` | `user:grade:change` | 自助改年级（频率校验、二次确认令牌） |
| PUT | `/api/users/me/profile` | `user:profile:update` | 昵称、选科等 |
| GET | `/api/users/me/grade-histories` | 登录 | 年级变更历史 |

### 10.2 家庭绑定

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/api/family/bindings` | `family:binding:request` | 家长按手机号/邀请码发起 |
| POST | `/api/family/bindings/{id}/confirm` | `family:binding:manage` | 孩子/监护人确认，写 `consent_at` |
| DELETE | `/api/family/bindings/{id}` | `family:binding:manage` | 解除绑定，状态 `revoked` |
| GET | `/api/family/children` | `family:report:read` | 孩子列表与当前年级 |
| PUT | `/api/family/children/{child_id}/controls` | `family:control:write` | 每日时长、青少年模式 |

### 10.3 组织与平台

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET/POST | `/api/org/classes` | `org:class:manage` | 班级列表/创建（校管） |
| POST | `/api/org/classes/{id}/members` | `org:student:manage` | 批量导入学生 |
| POST | `/api/org/assignments` | `org:teacher:assign` | 教师-班级-学科分配 |
| GET | `/api/admin/users` | `admin:user:manage` | 用户列表（按范围过滤、脱敏） |
| POST | `/api/admin/users/{id}/roles` | `admin:role:assign` | 授予/回收角色（禁止自授超管） |
| GET | `/api/audit/logs` | `audit:log:read` | 审计查询（按范围） |

### 10.4 学习域改造（向后兼容）

| 现有接口 | 改造 |
|---|---|
| `GET /api/learn/stats` | 增加可选 `student_id`（默认本人）；家长/教师按权限与范围校验 |
| `GET /api/learn/wrong-questions` | 同上；家长只读、教师不可读逐题 |
| `GET /api/learn/knowledge-tree` | 增加 `grade` 过滤；非当前年级教材返回 `GRADE_MISMATCH` 提示 |
| `POST /api/learn/start` | 增加 `grade`/`textbook_id` 一致性校验 |

### 10.5 考试域接口契约（v1.1 新增，CR-003 / EX-01~EX-03）

| 方法 | 路径 | 权限点 | 说明 |
|---|---|---|---|
| GET | `/api/exams` | `learn:exam:take` | 学生视角按 `student_visible_exam_clauses()` 过滤：`status=published`、年级匹配、非真题、非作业卷、班级卷限本班 |
| GET | `/api/exams/past-papers` | `learn:exam:take` | 真题库；真题不进入通用考试列表，避免入口虚标 |
| GET | `/api/exams/blueprints` | `content:exam:write` | App 组卷表单的可选蓝图；**须注册在 `/{exam_id}` 之前**，学生调用返回 403 |
| POST | `/api/exams/generate` | `content:exam:write` | 按蓝图组卷并发布（考试入库）；生成结果立即进入学生可见列表 |
| POST | `/api/exams/mock` | `learn:assignment:create` | 派发班级同卷模考 |
| GET | `/api/learn/home` | 登录 | `pending_exams[]` 与 `/api/exams` 共用同一可见性谓词，每条带 `entry` / `subject` / `window_state` |

App 侧入口：「我的 → 考试管理与发布」（`/exams/manage`）按 `content:exam:write` 显隐；首页「待办考试」卡按 `entry` 直达 `/exam/:id` 或 `/past-papers`。详见 [learning-page-design.md](./learning-page-design.md) §8.7。

---

## 十一、前端交互与年级选择

### 11.1 首次使用流程

```
注册/登录成功
  → GET /auth/me
  → 若 role=student 且 grade 为空
        → 进入「年级选择」页（全屏、不可跳过）
              ① 选择学段（小学/初中/高中）→ ② 选择年级 → ③ 确认教材版本（默认推荐）
        → PUT /users/me/grade + POST /me/textbooks/auto-bind
        → 进入学习页
  → 若 role=parent
        → 进入「绑定孩子」引导（可跳过，进入家长首页）
```

### 11.2 年级选择页设计

| 元素 | 规则 |
|---|---|
| 学段 Tab | 小学 / 初中 / 高中（默认按手机号归属地/上次选择） |
| 年级卡片 | 1-12，禁用与学段不符项；显示该年级主学科图标 |
| 教材预览 | 选择年级后展示将绑定的教材（如"数学 三年级上册 北师大版"），可展开修改 |
| 家长代选 | 儿童账号允许家长在绑定后修正，需二次确认 |
| 变更提示 | 修改年级时弹窗说明：将影响教材、练习范围与推荐，历史学情保留 |
| 频率限制 | 每学期 1 次自助修改；超出提示联系客服/校管 |

### 11.3 角色态界面差异

| 角色 | 首页 | 导航 |
|---|---|---|
| 学生 | 学习 | 学习 / 错题本 / 我的 |
| 家长 | 孩子学情 | 孩子 / 报告 / 我的（含"切换孩子"） |
| 教师 | 班级概览 | 班级 / 作业 / 我的 |
| 校管 | 学校概览 | 学校 / 班级 / 我的 |
| 运营/审核 | 内容工作台 | 内容 / 审核 / 我的 |

---

## 十二、实施计划与验收标准

### 12.1 分期

| 阶段 | 范围 | 交付 |
|---|---|---|
| **P0（必做）** | 学生年级必填与引导、stage/grade_group 派生、权限常量表、`require_permission`、家长绑定与 CHILD 范围、学习域接口范围校验、审计日志 | 年级选择页、权限守卫、家庭绑定接口、越权测试 |
| **P1** | 教师/班主任/校管角色、班级与授课分配、CLASS/SCHOOL 范围、班级学情聚合、管理端用户与角色 | 教师端页面、校管名册 |
| **P2** | 多角色表切换（user_roles）、权限可视化配置、内容审核双人复核、数据导出审计 | RBAC 表上线、配置后台 |

### 12.2 验收标准（可测）

| 编号 | 验收项 | 判定 |
|---|---|---|
| A1 | 学生注册不填年级 | 返回 422 `GRADE_REQUIRED`，前端进入引导页 |
| A2 | 客户端伪造 `stage=senior, grade=2` | 服务端覆盖为 `primary` 或拒绝，绝不落库错误组合 |
| A3 | 学生 A 请求学生 B 的 `/learn/stats?student_id=B` | 403 `SCOPE_DENIED`，审计留痕 |
| A4 | 家长仅能看到 active 绑定的孩子 | pending/revoked 绑定返回 403 |
| A5 | 教师只能访问所授班级与学科 | 跨班/跨科 403 |
| A6 | 校管不能操作外校学生 | 403；本校正常 |
| A7 | 角色变更后旧 Token | 立即 401 `TOKEN_REVOKED` |
| A8 | 权限矩阵覆盖 | 每个业务路由均声明权限点，CI 静态检查无遗漏 |
| A9 | 年级升级任务重复执行 | 不产生重复升级记录（唯一键） |
| A10 | 敏感操作审计 | 改角色/改年级/跨用户读取 100% 有日志 |
| A11 | 考试域接口权限（CR-003 / L18） | 学生调用 `GET /api/exams/blueprints` 返回 403；`content:exam:write` 账号返回 200 且仅列 `is_active` 蓝图 |
| A12 | 待办考试口径（CR-003 / L18） | 学生首页 `pending_exams` 与 `GET /api/exams` 完全一致；真题、作业卷、非本班班级卷、已交卷/关闭窗口卷不出现 |
| A13 | 考试入库与派发（CR-003 / L20） | `POST /api/exams/generate` 生成的普通卷立即出现在学生待办与列表；`POST /api/exams/mock` 仅 `learn:assignment:create` 可调用 |

> A11~A13 与主计划 `L18~L20`、`R-A16` 交叉引用，实现证据见 `project-task-plan.md` §6.22。

### 12.3 风险与对策

| 风险 | 对策 |
|---|---|
| 存量用户大量缺年级 | 登录强制引导 + 运营触达；未完成仅开放"公开教材浏览" |
| 家长绑定纠纷 | 双端确认 + 解除即时生效 + 审计 |
| 教师端一期范围蔓延 | 严格限定"布置/查看/批改"三件事，不做教研协作 |
| 权限点膨胀 | 命名规范 `domain:resource:action`，每季度清理未使用权限 |
| 多角色并集提权 | 按请求所需权限选范围，不做全局并集 |

---

## 十三、附录：权限点全量清单

### 13.1 命名规范

```
<domain>:<resource>:<action>
domain  ∈ learn | content | family | org | admin | audit | support | system
action  ∈ read | write | create | delete | execute | manage | assign | decide
```

### 13.2 清单

| 权限点 | 说明 | 绑定范围 |
|---|---|---|
| `learn:content:read` | 浏览教材/章节/公开知识点 | NONE |
| `learn:kp:study` | 进入知识点学习与讲解 | SELF / CLASS |
| `learn:practice:start` | 开始自适应练习 | SELF |
| `learn:practice:submit` | 提交作答 | SELF |
| `learn:stats:self:read` | 查看本人学情 | SELF |
| `learn:stats:child:read` | 查看孩子学情 | CHILD |
| `learn:stats:class:read` | 查看班级学情（聚合） | CLASS |
| `learn:wrong:self` | 本人错题本读写 | SELF |
| `learn:wrong:annotate` | 标注错因 | SELF |
| `learn:review:today` | 今日到期复习 | SELF |
| `learn:exam:take` | 参加考试 | SELF |
| `learn:exam:report:self` | 本人考试报告 | SELF |
| `learn:assignment:create` | 布置作业/测验；v1.1 起控制 `POST /api/exams/mock` 班级同卷模考派发 | CLASS |
| `learn:exam:grade` | 批改主观题 | CLASS |
| `content:textbook:write` | 教材/章节维护 | ALL |
| `content:kp:write` | 知识点维护 | ALL |
| `content:question:write` | 题库维护 | ALL |
| `content:exam:write` | 试卷模板维护；v1.1 起控制 App `/exams/manage` 入口显隐、`GET /api/exams/blueprints` 与 `POST /api/exams/generate` | ALL |
| `content:review:decide` | 内容审核 | ALL |
| `content:publish` | 内容上下架 | ALL |
| `family:binding:request` | 发起绑定 | SELF |
| `family:binding:manage` | 确认/解除绑定 | SELF / CHILD |
| `family:control:write` | 时长与青少年模式 | CHILD |
| `family:report:read` | 孩子报告 | CHILD |
| `org:class:manage` | 班级管理 | SCHOOL |
| `org:student:manage` | 学生名册 | SCHOOL / CLASS |
| `org:teacher:assign` | 教师分配 | SCHOOL |
| `admin:user:manage` | 用户管理 | SCHOOL / ALL |
| `admin:role:assign` | 角色分配 | SCHOOL / ALL |
| `audit:log:read` | 审计日志 | SCHOOL / ALL |
| `support:ticket:manage` | 工单 | SELF / ALL |
| `system:config:write` | 系统配置 | ALL |
| `user:profile:update` | 本人资料 | SELF |
| `user:grade:change` | 年级修改 | SELF / SCHOOL |
| `data:export` | 数据导出 | SCHOOL / ALL |

### 13.3 与现有代码的映射

| 现有实现 | 迁移后 |
|---|---|
| `User.role ∈ {student,parent,admin}` | 主角色 + 可选附加角色；`admin` → `super_admin` |
| `require_admin` | `require_permission("*")` 或 `require_permission("admin:user:manage")` |
| `learn.py` 内 `current.id` 硬编码 | `require_student_access("<permission>")` + `resolve_student_ids` |
| `schemas.UserCreate.role` 仅两种 | 注册仍仅开放 student/parent；其他角色由管理端授予 |
| `UserOut` 无 grade_group | 增加派生字段与 `permissions` 聚合 |

---

> **落地建议**：先做 P0 的"年级必填 + 权限常量 + 范围函数 + 家长绑定"，这三项能同时解决"年级缺失"和"数据越权"两个最高风险；教师/校管能力在 P1 通过数据驱动扩展，无需改动学习域核心逻辑。
