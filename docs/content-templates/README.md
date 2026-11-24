# 题库 / 知识库作者模板

用于教研按学科手工补充题目与知识点。每个学科一份 JSON（文件名即学科代码），复制后修改内容即可。

## 目录

| 文件 | 学科 | 默认教材 |
|---|---|---|
| `chinese.json` | 语文 | 人教版 1 年级上册 |
| `math.json` | 数学 | 北师大版 1 年级上册 |
| `english.json` | 英语 | 沪教牛津版（2024）·深圳1 年级上册 |
| `physics.json` | 物理 | 人教版 8 年级上册 |
| `chemistry.json` | 化学 | 人教版 9 年级上册 |
| `biology.json` | 生物 | 人教版 7 年级上册 |
| `history.json` | 历史 | 部编版 7 年级上册 |
| `geography.json` | 地理 | 湘教版 7 年级上册 |
| `politics.json` | 道德与法治 | 人教版（部编）7 年级上册 |

> 模板里的教材/年级可改；同一份文件只对应「一个学科 + 一个年级 + 一个教材版本 + 一个学期」。
>
> 每份模板都是可直接导入的完整示例：含 1 个节 + 3~4 个知识点（带前置关系），以及 `choice`、`multiple`、`judge`、`fill`、`answer` 五种题型各 1 道，可作为新增内容时的结构参照。

## 深圳教材版本基线（罗湖 / 福田 / 南山公立学校）

下表以**罗湖区、福田区、南山区公立学校**现行教材为准，用于确定模板中的 `version`、`grade` 与章节结构。三区在项目覆盖的 9 个学科上版本一致；如个别学校另有选用，以学校实际发放的教材为准。本表不含科学、信息科技、体育、艺术等非项目覆盖学科。

### 小学（1-6 年级）

| 学科 | 教材版本 | 出版/说明 |
|---|---|---|
| 语文 | 统编版（人教版） | 人民教育出版社，部编教材 |
| 数学 | 北师大版 | 北京师范大学出版社 |
| 英语 | 沪教牛津版（2024）·深圳 | 上海教育出版社 / 牛津大学出版社，1-6 年级 |
| 道德与法治 | 统编版（人教版） | 人民教育出版社，部编教材 |

### 初中（7-9 年级）

| 学科 | 教材版本 | 出版/说明 | 开设年级 |
|---|---|---|---|
| 语文 | 统编版（人教版） | 人民教育出版社，部编教材 | 7-9 |
| 数学 | 北师大版 | 北京师范大学出版社 | 7-9 |
| 英语 | 沪教牛津版（2024）·深圳 | 上海教育出版社 / 牛津大学出版社（7-9 每册 8 单元） | 7-9 |
| 道德与法治 | 统编版（人教版） | 人民教育出版社，部编教材 | 7-9 |
| 历史 | 统编版（人教版） | 人民教育出版社，部编教材 | 7-9 |
| 地理 | 湘教版 | 湖南教育出版社 | 7-8 |
| 生物学 | 人教版 | 人民教育出版社 | 7-8 |
| 物理 | 人教版 | 人民教育出版社 | 8-9 |
| 化学 | 人教版 | 人民教育出版社 | 9 |

### 高中（10-12 年级）

| 学科 | 教材版本 | 出版/说明 |
|---|---|---|
| 语文 | 统编版（人教版） | 人民教育出版社，部编教材 |
| 数学 | 人教版A版 | 人民教育出版社 |
| 英语 | 外研版 | 外语教学与研究出版社 |
| 思想政治 | 统编版（人教版） | 人民教育出版社，部编教材 |
| 历史 | 统编版（人教版） | 人民教育出版社，部编教材 |
| 地理 | 人教版 | 人民教育出版社 |
| 物理 | 人教版 | 人民教育出版社 |
| 化学 | 人教版 | 人民教育出版社 |
| 生物学 | 人教版 | 人民教育出版社 |

> 义务教育阶段自 2024 年秋季起，起始年级陆续使用新修订教材；表中版本为现行版本。
>
> 内置教材矩阵已按上表对齐：高中数学 `人教版A版`、英语 `外研版`、地理 `人教版`（初中地理仍为 `湘教版`）；小学 1-6 年级已补齐道德与法治教材记录。
>
> 模板 `version` 必须与库中版本名完全一致：语文入库为 `人教版`；历史入库为 `部编版`；**道德与法治入库存量记录为 `部编版` 与 `人教版（部编）` 两种，2026-11-23 起新内容与英语一律按新口径写 `人教版（部编）` / `沪教牛津版（2024）·深圳`**；小学与初中英语入库已统一为 `沪教牛津版（2024）·深圳`。表中“统编版（人教版）”“沪教牛津版（2024）·深圳”是教材叫法，`version` 请按下句的入库字符串原样填写。
>
> **2026-11-23 版本口径变更（深圳初中教材版本对齐，详见 `docs/sz-textbook-version-alignment.md`）**：库内英语 `version` 由 `牛津深圳版` 改为 `沪教牛津版（2024）·深圳`；道法由 `部编版` 改为 `人教版（部编）`；英语 7-9 章节已按上教版新教材重建为**每册 8 单元**（9 下为占位章节「待发布·上教版新教材九年级下册」，不铺题）。旧口径的 `牛津深圳版` 字符串在库内已不存在，写旧名会导致版本校验失败。

## 导入

> 目标库由 `DATABASE_URL` 决定：默认 `ailearning_dev.db`，真机联调使用 `ailearning_device.db`。两库已于 2026-11-07 统一升级到 head 与教材版本字符串（基线 146 教材 / 126 章 / 337 知识点 / 646 题）；11-08 批次入库后 **dev 为 657 章 / 581 知识点 / 1004 题、同名 0 组**（章节数含 11-07 的教材目录导入），device 仍停在基线量，需要时对 device 重跑同一批导入。

在 `backend` 目录执行（先 `alembic upgrade head`）。目录约定：`templates/` 学科模板、`daily/<subject>/g<grade>/` 每日产出、`baseline/` 基线快照、`ledger/` 台账、`logs/` 运行日志。

```powershell
.venv\Scripts\python.exe -m scripts.import_content --path ..\docs\content-templates\templates\math.json
.venv\Scripts\python.exe -m scripts.import_content --path ..\docs\content-templates\templates --dry-run
```

- 默认幂等：同章节、同题干、同题型已存在则跳过；加 `--overwrite` 覆盖题面/答案/解析。
- 批量：`--path` 传目录时递归读取所有 `*.json`（跳过文件名以 `_` 开头的模板），可一次导入多学科、多年级文件。
- 过滤：`--pattern "math_g*_first_*.json"` 只导入匹配的当日文件，不影响其他模板。
- 清单：`--manifest ..\docs\content-templates\_import-manifest.json` 记录文件 hash、计数、状态与目标库；相同文件再次运行自动跳过，换库或重建库后旧记录自动作废。
- 事务：每个文件独立提交，单个文件校验/导入失败不影响同批其他文件（命令最终返回码为 1，列出失败文件）。
- `--dry-run` 只校验、统计并回滚，不写库；失败会指出文件与具体条目。
- 一个文件只对应「一个学科 + 一个年级 + 一个教材版本 + 一个学期」，不同年级/版本请拆分为多个文件。
- 模板之间不要互相引用知识点：题目 `knowledge_point` 只能引用本文件 `knowledge` 或库中已有知识点。库内同名节点已于 2026-11-07 全量去重（0 组歧义）；若仍出现多个同名会拒绝导入并提示显式定义。

### 每日自动化入库

每日教研产出的 JSON 放在 `daily\<subject>\g<grade>\`，按以下五步入库（目标库先确认）：

```powershell
# 0) 备份目标库（建议；防 upsert 覆盖旧讲解，默认写 backend\build\backups）
.venv\Scripts\python.exe -m scripts.db_backup

# 1) 离线自检（不连库；基线读 latest 固定名，不要写死日期）
python ..\docs\content-templates\_validate_daily.py ..\docs\content-templates\daily `
  --kp-baseline ..\docs\content-templates\baseline\_knowledge-points-baseline_latest.json

# 2) 服务端试跑，只针对当日文件
.venv\Scripts\python.exe -m scripts.import_content --path ..\docs\content-templates\daily `
  --pattern "*_20261107.json" --dry-run

# 3) 正式导入并写清单（逐文件事务）
.venv\Scripts\python.exe -m scripts.import_content --path ..\docs\content-templates\daily `
  --pattern "*_20261107.json" --manifest ..\docs\content-templates\_import-manifest.json

# 4) 导入后重建两份基线（只读查库，同时覆盖 _latest）
.venv\Scripts\python.exe -m scripts.build_kp_baseline --output-dir ..\docs\content-templates\baseline
.venv\Scripts\python.exe -m scripts.build_chapters_baseline --output-dir ..\docs\content-templates\baseline
```

失败文件会记录为 `failed`，修复 JSON 后重跑即可；已成功的文件由清单跳过。基线文件名带日期的是归档，**任务与自检只读 `_latest`**；重建库后 manifest 会自动作废旧记录。

## 顶层结构

```json
{
  "subject": "math",
  "grade": 1,
  "version": "北师大版",
  "semester": "first",
  "knowledge": [],
  "chapters": []
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `subject` | 是 | 学科代码：`chinese/math/english/physics/chemistry/biology/history/geography/politics` |
| `grade` | 是 | 1~12 |
| `version` | 是 | 教材版本名，与库中字符串逐字一致（如「人教版」「北师大版」「沪教牛津版（2024）·深圳」「人教版（部编）」「部编版」「湘教版」） |
| `semester` | 否 | `first`（上册，默认）/ `second`（下册） |
| `knowledge` | 否 | 知识树：先 `section`（节），再 `point`（最小知识点）；只补题目时可省略 |
| `chapters` | 否 | 章节与题目；章节名与教材目录一致；只补知识点时可省略 |

> `knowledge` 与 `chapters` 至少填写一项。只补题目时，`knowledge_point` 可引用库中已有知识点（按学科+年级+名称匹配）。

## 知识库条目

```json
{
  "node_type": "point",
  "name": "10以内加法",
  "parent": "10以内数的认识与加减法",
  "order_index": 1,
  "weight": 1.0,
  "explanation": "理解加法的含义，能正确计算 10 以内的加法。",
  "prerequisites": ["10以内数的认识"]
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `node_type` | 否 | `section` 或 `point`（默认 `point`） |
| `name` | 是 | 同一文件内唯一；`point` 与 `section` 同名时导入会自动给 point 加「（要点）」后缀，后续引用请使用带后缀的实际名称 |
| `parent` | point 必填 | 所属 `section` 的 `name`，必须在本文件 `knowledge` 中定义 |
| `explanation` | 建议 | 1~3 句讲解，供知识点详情页展示 |
| `prerequisites` | 否 | 前置知识点名称数组，仅解析本文件内名称 |
| `order_index` / `weight` | 否 | 排序与掌握度权重，默认 0 / 1.0 |

## 题库条目

```json
{
  "name": "加与减（一）",
  "order_index": 1,
  "summary": "10 以内加减法的意义与计算。",
  "questions": [
    {
      "q_type": "choice",
      "stem": "3 + 4 = ?",
      "options": ["5", "6", "7", "8"],
      "answer": {"value": "C"},
      "analysis": "3 加 4 得 7，所以选 C。",
      "difficulty": 1,
      "knowledge_point": "10以内加法",
      "tags": ["加法", "10以内"],
      "status": "published"
    }
  ]
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `q_type` | 是 | `choice` 单选 / `multiple` 多选 / `judge` 判断 / `fill` 填空 / `answer` 主观题 |
| `stem` | 是 | 题干；当前客户端仅渲染 `stem`，不要放图片/长材料 |
| `options` | 选择/判断必填 | 字符串数组（自动编 A/B/C…）或 `[{"key":"A","text":"…"}]`；判断题可省略，默认 T/F |
| `answer.value` | 是 | 单选：`"C"`；多选：`["A","C"]`；判断：`"T"/"F"`；填空：`"340"` 或多答案列表 `["凹液面最低处","凹液面的最低处"]`；主观题：参考答案文本 |
| `analysis` | 建议 | 解析文本，展示在作答反馈中 |
| `difficulty` | 否 | 1~5，默认 2 |
| `knowledge_point` | 是 | 挂载的知识点 `name`（本文件内的 point/section，或库中已有知识点） |
| `tags` | 否 | 字符串数组 |
| `status` | 否 | `published`（默认）/ `draft`（待审核，练习/组卷不采用）/ `offline` |

## 来源与版权登记

题目与知识点都支持来源字段。**标注来源不等于获得授权**：原创内容标 `original`；引用或改编教材、真题、教辅时必须如实登记，并确认已取得授权或属于允许使用的范围。

| 字段 | 适用 | 说明 |
|---|---|---|
| `source_type` | 题目 / 知识点 | `original` 原创（默认）/ `adapted` 改编 / `licensed` 已授权 / `public` 公共领域 / `external` 外部导入待核 |
| `source_name` | 非原创必填 | 来源名称，如「人教版八年级上册」 |
| `source_ref` | 否 | 页码、题号或 URL |
| `copyright_owner` | 否 | 版权方 |
| `license_note` | `licensed` 必填 | 授权说明或协议编号 |
| `adapted_from` | `adapted` 题目必填 | 改编自哪道题或哪份材料 |

导入校验规则：

1. `source_type` 非 `original` 时必须填写 `source_name`；
2. `licensed` 必须填写 `license_note`；
3. 题目 `adapted` 必须填写 `adapted_from`；
4. 题目 `external` 的 `status` 必须为 `draft`，复核后才可转 `published`。

模板中的知识点与首题已演示 `original` 写法；复制新增时请按实际来源填写，不要把改编或引用内容标成 `original`。

## 出题质量要求

1. 题干独立可答，不依赖图片、音频或上文；不含「如图」「上题」等指代。
2. 选项互斥且长度接近，不出现「以上都对」这类不稳定选项（多选请用 `multiple`）。
3. 填空题答案能唯一判定；多写法用答案列表穷举，不要用「略」。
4. 主观题必须给参考答案与评分要点，建议同步给出 `analysis`。
5. 解析写明关键步骤或易错点，不写「因为答案如此」。
6. 每题至少挂 1 个知识点；新增知识点时先补 `knowledge`，再补题目。
7. 单文件建议不超过 200 题，按「章节」拆分文件便于评审与回滚。
8. 提交前先跑 `--dry-run`；上线前题目 `status` 建议先 `draft`，走内容复核后再 `published`。

## 整册教研数据口径（2026-11-14 起，整册重跑 / 定时任务都适用）

> 本节是「整册重跑（`rerun_packs/` + `_rerun_books.py`）」与「每日增量任务」共用的硬口径；模板级要求见 §出题质量要求，内容包写法见 `rerun_packs/_PACK_SPEC.md` §8–§10。

### 1. 统一骨架与当前基线

- 范围：g1–g9 全学科**上下册统一骨架**，共 **92 册**；骨架索引唯一可信来源 `exports/review_20261112/rerun_skeleton_index_g1g9_unified_20261113.json`（`books[]` 的 `chapters` 为该册官方章序）。
- 当前基线（2026-11-14 骨架纠偏后）：**92 册 / 608 章 / 2432 知识点 / 11678 题**；纠偏前为 92 / 618 / 2472 / 11870。
- 基线口径：`daily_rerun/` 与 `daily_consolidated/` 各 92 份逐册一致，且逐册题量与库内题行精确相等；`backend\ailearning_dev.db` 总表以「册 / 章 / 知识点 / 题目」四项对齐。

### 2. 分册章域（禁止跨册重复章）

- 同一学科同一年级的两册**不得出现同一章**。physics g9 原骨架曾把上册 10 章整份复制给下册（第十三章 内能～第二十二章 能源与可持续发展 ×2），2026-11-14 已按人教版实际分册修正：上册 13–18 章（6 章）、下册 19–22 章（4 章）。
- 落地方式：`_rerun_books.py` 的 `CHAPTER_SCOPE`（键 = 学科/年级/学期）+ `apply_chapter_scope()`，在 `load_packs` 阶段裁剪，留痕 `_rerun.chapter_scope`；同时修正骨架索引的 `chapters / chapter_count`。
- 语文各年级「第一/二…单元」、数学 g4/g5/g6「总复习」在上下册同名，属教材真实结构（章属于不同 textbook），**不是缺陷**，不需要改名。
- 新增册要拆上下册，必须先登记 `CHAPTER_SCOPE`，再改骨架索引，然后全量重组装；漏改骨架会触发自检「章名与官方骨架不一致」。

### 3. 跨册同题处置（去前缀比对）

- 判据：剥离 `（学科年级册别·章名）` 前缀后，按 **(题干, 题型)** 跨册比对；同题即视为重复。
- 处置：跨学科重复 → 按学科归属改写「不属于本学科」的一侧；同年级同学科跨册重复 → 改写下册侧；跨年级同学科重复 → 判定为螺旋复现，保留。
- 铁律：**只改题不删题**，改写后题量回到本册基线；改写登记在 `_rerun_books.py` 的 `DUPLICATE_REWRITES`（原题干必须逐字一致，含空格），由 `apply_duplicate_rewrites()` 执行。
- 复核：`python _find_same_content.py`；当前结果为 24 组，全部为跨年级同学科。

### 4. 每日任务 / 整册重跑的结构性防重规则

1. **题干不得跨册重复**：同一个题干在 92 册里只能出现一次（跨年级螺旋复现除外，需人工确认）；系统侧由 `disambiguate_stems()` 补册次前缀兜底，计数写 `_rerun.stem_dedup`，但**前缀只是兜底，不是许可**。
2. **多选题统一 2 真 2 假**：正确项固定 A、C，错误项 B、D，`answer` 固定 2 项；题干带册次（`关于{年级}年级{上/下册}「{章名}」的相关内容，下列说法正确的有哪些？`）；`knowledge_point` **固定本章首个题的知识点**（不得挂到跨章取材的节点，否则硬门禁 `section_shared_questions_0` 会判 FAIL）。
3. **同 section 的题不得出现在 >1 章**（硬门禁 `section_shared_questions_0`）。
4. **判断题**：每册至少 5 道「真」判断，且题干 ≥5 字、句末带标点；「真」项不足会在校验器中表现为「缺少题型 multiple」。
5. **难度分布**照 40/40/20 归一；主观题答案 ≥8 字，不得写「略」开头的空答案（`略读` 这类正文也需改写，避免命中「略」）。
6. **题干泛化词**禁用：`更可取的学习做法`、`可以先梳理`、`举一个生活中用到`、`结合实例分析比单纯背诵`、`值得提倡的`、`知识脉络`。

### 5. 台账与留痕要求

- 每次整册重跑必须留痕：`_rerun` 内的 `normalized / supplemented / stem_dedup / duplicate_rewrites / chapter_scope / status`；
- 每次入库必须留痕：机读校验（`_validate_daily.py --json-out`）、门禁（`_check_book_gate.py --json-out`）、审计（`_audit_g1g9.py`）、stale 清理（`_stale_check.py`，dry-run 与 apply 各一份）、逐册核对（`_verify_books_vs_db.py`）；
- 骨架/章域变更还必须留痕：骨架索引备份、`_scope_cleanup.py` 报告（记录被删章节与随删题目数）。
