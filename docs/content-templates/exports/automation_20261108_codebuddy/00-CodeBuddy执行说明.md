# 每日教研导出包 · CodeBuddy 可执行改写版（2026-11-08）

把 `..\automation_20261108\`（豆包定时任务导出）改写成我在本机 **CodeBuddy 会话里能直接跑** 的版本：把原本"写在提示词里、靠模型自觉执行"的确定性动作（批次日期、锁、快路径、自检命令、统计、台账、日志）下沉到脚本，把 9 段 query 改写成可以直接粘贴的新会话提示词与可注册的自动化载荷。

**原文一个字都没动**：`AI每日教研自动化任务-提示词设计.md`、`exports\automation_20261108\` 下的 5 个文件、`content-templates\` 下现有脚本与 JSON 全部保持原状；本目录是新增的并列改写版，写动作默认只读。

## 目录内容

| 文件 | 用途 |
|---|---|
| `00-CodeBuddy执行说明.md` | 本文件：差异、前置、用法、验证记录 |
| `01-主提示词.md` | 唯一指令源：可直接粘贴到全新会话的通用提示词 + 工具映射表 |
| `02-九条任务-CodeBuddy版.md` | 原 9 段 query 的逐条改写（参数、学科规则、命令、边界），附差异对照 |
| `tasks.json` | 9 条任务的唯一参数源（学科/年级/版本/学期/错峰分钟/学科规则/路径/班次策略） |
| `_run_daily.py` | 纯标准库驱动：`plan / progress / context / validate / commit / finish / lock / outline / prompt / payload(s) / list` |
| `03-自动化注册清单.json` | 27 条 `automation_update` 载荷（9 学科 × 3 班次，启用形态 **B**：`BYHOUR=2/12/21`）**审阅稿**：默认 `PAUSED`、从未注册，顶层 `registration.allowed=false`，**不可直接注册** |
| `run.ps1` | **一键入口**：默认跑只读 plan 并打印「参数已展开、BATCH_DATE 已固定」的完整提示词；`-Action check/commit` 做只读预检或写完 JSON 后的一键收尾 |
| `run.cmd` | `run.ps1` 的最短包装，直接 `run.cmd -Subject math -Shift 02` |
| `run_all.ps1` | **全学科一键入口（只读）**：默认打印 9 学科统一计划 + 一条可执行全科提示词；`-Action` 仅 `run/verify/plan/prompt` |
| `run_all.cmd` | 全学科入口的最短包装，直接 `run_all.cmd` |
| `ops.ps1` / `ops.cmd` | **独立人工运维入库入口**：`import/import-dry/restore`；须显式 `-Date` + `-ConfirmToken I_KNOW`（脚本不代填）、`restore` 的 `-BackupPath` 须存在，并在控制台输入运行时一次性 6 位确认码（第五轮加固）；`run_all.*` 已无入库 Action |
| `_run_daily.py` 新增命令 | `all-plan`（9 学科计划）、`all-verify`（统一核实）、`all-prompt`（全科提示词）、`progress`（章节指针）、`ledger-sync`（按 JSON 就地重算台账，支持 `--force-next` 强制回写下一节）、`log-sync`（运行日志归一为一张明细表/唯一表头）——后两者为人工运维命令，写动作需 `--confirm I_KNOW`，教研会话禁用；**不含任何连库能力** |
| `db_ops.py` | **独立人工运维脚本**：备份/入库/回退/**变更留痕**，写库动作强制 `--confirm I_KNOW`；`audit --since <备份.db> [--current <db>] --out <json>` 为只读 diff，产出机器可读记录；教研会话禁止调用 |
| `db_op_<时间戳>.json` | 库手术的机器可读记录（删除/新增/改动 id、字段前后值、受影响题数、回滚命令）：`db_op_20261108_170620.json`（删 452）、`db_op_20261108_172843.json`（板块改挂 + 456 合并）、`db_op_20261108_182439.json`（Letters 板块 + 3 题归位）、`db_op_20261108_190935.json`（`Alphabet order` 补第 4 题）。**以后每次改库都要补一份** |
| `..\_archive\`（在 `docs\content-templates\` 下） | 历史内容文件的改前副本：`english_g1_first_20261107.pre-remap.json`（remap 前，sha 与导入期一致）、`english_g1_first_20261107.pre-q4-add.json`（补题前）+ `.provenance.txt`。**改历史 JSON 前必须先存一份**（见 `04` §3.1） |
| `chapter_audit.py` | **只读**巡检脚本：库内章节名 vs **官方章节骨架**（`baseline/_skeleton_first|_skeleton`），输出占位/旧样章清单、`order_index` 撞号、官方章序与骨架是否一致（`04` §3.2）。不改库 |
| `chapter_audit_20261108.json` | 占位章节巡检结果（**阶段 4 删除后**）：146 册 / **618 章节** → **占位章 0 / 未标记 0 / 撞号 0 / 官方章序与骨架不一致 0**，EXIT=0 |
| `05-占位章节清理立项.md` | **立项书**：占位章节清理的目标、非目标、R-A/R-B/R-C 判定规则、三阶段划分、风险与回滚、验收标准 |
| `chapter_cleanup.py` | **阶段 1 执行脚本**（人工运维，写库需 `--confirm I_KNOW`）：备份 → 迁移题目 → 删空置旧章 / 标记 R-C 占位章 → 官方章序回写 → 自检 → 产出 `db_op_*.json`；`--dry-run` 只算不写，`--alias-only` 只重生成导入别名表 |
| `chapter_cleanup_plan_20261108.json` | **判定表**（机器可读，唯一事实来源）：39 个旧样章逐条给规则（R-A/R-B/R-C）、目标官方章节、依据文字；另有 24 条 R-C 的原因与归属建议 |
| `chapter_pending_map.py` / `chapter_pending_map_20261108.json` | **阶段 2 产出**（只读）：24 个 R-C 占位章 / 130 题的归属确认清单，含每册教材真实章节候选、题目知识点父链、原因/建议/风险，供业务确认 |
| `db_op_20261108_200923.json` | 占位章节清理的库变更留痕：chapters 657→642、questions 1087→1087（零丢失）、迁移 167 题、删除 15 章、标记 24 章、序回写 2 处、考试章节引用修正 2 条、备份与回滚命令 |
| `chapter_drop_legacy.py` | **阶段 4 执行脚本**（人工运维，写库需 `--confirm I_KNOW`）：删除 24 个旧版占位章 + 130 题 + 61 个随之变空的独占知识点，并修 `exams.chapter_ids` 的悬空/残缺引用；`--dry-run` 只算不写 |
| `db_op_20261108_204703.json` / `db_op_20261108_204908.json` | 阶段 4 留痕：前者记删除明细（24 章 / 130 题 / 61 知识点）与备份 `ailearning-backup-20261108-204703.db`；后者记 3 份考试章节引用重挂与备份 `ailearning-backup-20261108-204908.db` |
| `chapter_pending_map.py` / `chapter_pending_map_20261108.json` | **阶段 2 产出，已作废**（2026-11-08 用户改判为「旧版数据删掉」，不再需要归属确认）；保留作留痕 |
| `coverage_gap.py` / `coverage_gap_20261108.json` | **覆盖缺口巡检**（只读）：管「齐不齐」——每册教材的官方章数 / 有题章数 / 0 题章清单 / 整册空册清单，并与 `tasks.json` 的待重跑队列对账；与 `chapter_audit.py`（管「干不干净」）分工（`04` §3.5） |
| `mark_legacy_json.py` | 给 11-07 的 8 份 math JSON 打 `_legacy` 标记（改前逐字节副本 + provenance + 同步 manifest 当前值两列）。**人工运维专用**，见 `04` §3.7 禁令 |
| `migrate_manifest_3col.py` | 把 `_import-manifest.json` 从单列 `sha256` 迁到**三列语义**（`imported_sha256` 导入当刻永不改写 / `current_file_sha256` 盘上现值 / `imported_content_sha256` 剥元数据后的内容哈希），带逐字节副本 + provenance |
| `..\baseline\_skeleton_first\_skeleton\` | **官方章节骨架**（占位判定的唯一基准）：每册教材的目录章名与序；本轮补齐了缺失的 `math g9` 上/下册骨架 |
| `04-一键执行与入库操作手册.md` | **后续重复调用看这一份**：固定路径、一键教研、核实、一键入库、回退、目标库/真机验证、参数速查、实测记录，命令复制即用 |

> 只想按流程重复执行，直接打开 `04-一键执行与入库操作手册.md`，改 `$Date` 即可；本文件保留设计差异与完整验证记录。

## 全学科一键：当天 9 学科 + 核实 + 可重复执行

**一条命令（默认当天、02 进攻班；全程只读，可反复运行）：**

```powershell
& "D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\run_all.cmd"
```

等价完整写法：`powershell -NoProfile -ExecutionPolicy Bypass -File "D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\run_all.ps1" -Date 20261108 -Shift 02`

它会做两件事：

1. 打印 `all-plan` 的只读汇总：9 学科 / 46 年级里哪些 `done`、哪些 `missing`、哪些 `repair`，以及每个年级今天应做的 `next_section`。
2. 打印**一条可直接粘贴到全新 CodeBuddy 会话的全科提示词**：会话按 `tasks.json` 顺序逐学科闭环（`plan → lock → context → write_to_file → validate → commit → finish`），全部做完后自动跑 `all-verify --strict` 核实，并汇报 9 学科汇总表。

**独立核实结果（只读，退出码即结论）：**

```powershell
& "D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\run_all.cmd" -Action verify -Strict -Date 20261108
```

`0` = 46 个年级文件齐、自检 0 错误、章节在大纲内、知识点/题量/题型达标、无重复题干、分布检查无提醒、校验器 0 提醒；`1` = 有 `missing` / `fail` / `warn`，输出会逐条列出（不加 `-Strict` 时只把 `fail` 判为不通过）。`warn` 现在包含三类：分布提醒、规格提醒、`_validate_daily.py` 的 `[提醒]`。也可直接调 `_run_daily.py all-plan|all-verify|all-prompt --date 20261108 --json`。

### 为什么可以重复执行、不会卡在同一章节

- **同日重跑**：`all-plan` 重算每个年级状态，当天文件已存在且自检通过 → `done/skip`，不重写、不加 `_r2`、不重复出题；只补 `missing`、修 `repair`。全部完成后重复运行只是空转汇总，`all-verify --strict` 通过。
- **断点续做**：46 个年级单次会话可能跑不完；时间/上下文不足时立即停手，已完成年级已逐年级落盘并在日志写明剩余项，**下次原样重跑同一条命令从断点继续**。这是允许分批跑完全部学科的原因，不是失败。
- **换日重跑**：前一天文件进入 `progress_of()` 的已覆盖集合，`next_section` 按大纲顺序自动前进；今天只做这一节，不回头重做、不跳节；同一节连续 ≥2 天必须标注「同一节第 N 天 / 第二轮」。模拟验证（不写文件）：化学 g9 `课题2 化学实验与科学探究 → 课题1 我们周围的空气`、语文 g1 `4 日月山川 → 语文园地一`、数学 g4 `人口普查 → 大豆产量`，指针均前进。
- 每次 `commit` 把真实 section 与具体下一节写进台账/日志，形成闭环；补漏班（12/22）按原文不推进新节。

| 参数 | 默认 | 说明 |
|---|---|---|
| `-Action` | `run` | `run`=计划+全科提示词；`plan`=只看计划；`prompt`=只出提示词；`verify`=核实结果 |
| `-Date` | 当天 `yyyyMMdd` | BATCH_DATE，固定不变 |
| `-Shift` | `02` | `02` 进攻班 / `12`、`22` 补漏班 |
| `-Strict` | 关 | `verify` 时把缺文件与内容提醒也判为未通过 |
| `-Json` / `-OutFile` | 关 / 空 | 机器可读输出 / 另存提示词为 UTF-8 无 BOM 文件 |

> 当前 20261108 实测（第三轮彻底更正后）：`all-plan` 为 9 学科 / **46 年级**，`done 23`、`missing 23`、`repair 0`、6 个学科无待办；`all-verify` 为 **23 个 `ok` / 0 个 `warn` / 0 `fail` / 23 缺文件**（另有 20 条「台账·日志未覆盖历史文件」记录提示，不影响内容核实）。物理 g8（4 条）与地理 g8（2 条）的「数值填空无算式」提醒已通过补写真实算式消除，校验器规则未放宽。非严格模式退出码 0；`-Action verify -Strict` 仍返回 1，**仅因 23 个年级待产出**（缺文件在严格模式计入未通过），属正常信号而非脚本故障。此前「5 `ok` / 17 `warn`」与「21 `ok` / 2 `warn`」是各阶段暴露的真实缺口，修复过程见「评审整改」「复评整改」「第三轮整改」。

## 人工运维入库（ops.cmd：先备份 → 试跑 → 正式导入 → 核实 → 回退）

教研 JSON 的**生成流程永远不连库**；入库是独立动作，必须显式调用。目标库由 `backend\app\core\config.py` 的 `settings.database_url` 决定（当前 `sqlite:///./ailearning_dev.db`），可用环境变量 `DATABASE_URL` 覆盖；一键入库只支持 SQLite。

> **2026-11-08 评审整改 + 第四轮修正**：入库/回退实现已从 `_run_daily.py` **整体摘除**，搬到独立人工运维脚本 `db_ops.py`（写库强制 `--confirm I_KNOW`）。第四轮把 `import/import-dry/restore` 从 `run_all.ps1` 的 `ValidateSet` **彻底移除**，另置 `ops.cmd` / `ops.ps1`，并要求人工显式 `-ConfirmToken I_KNOW`（脚本不再代填）；`run_all.*` 现在只有 `run/verify/plan/prompt` 四个只读 Action，教研会话不可能「顺手入库」。`01-主提示词.md`、`02` 九条 query、`tasks.json` 的 `boundary` 与 27 条载荷 prompt 均已写入显式禁令。下文历史实测记录里的 `run_all.cmd -Action import` 是 11-08 当时的入口，现已失效，实际命令见下方代码块。第五轮又给闸门加了两道：`-Date` 必须显式给出（不再默认今天）、`restore` 的 `-BackupPath` 必须指向真实存在的备份，并在控制台输入运行时打印的一次性 6 位确认码（`Read-Host`）；因此「照示例复制 `I_KNOW` 一条命令就写库」已不成立。

```powershell
# 人工运维入库：先备份 → 离线自检 → dry-run 试跑 → 正式导入（带 manifest）→ 前后统计与逐题核实
& "D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\ops.cmd" -Action import -Date 20261108 -ConfirmToken I_KNOW

# 只改了已有题目的字段（如 difficulty）时，加 -Overwrite 让字段同步入库
& "...\ops.cmd" -Action import -Date 20261108 -Overwrite -ConfirmToken I_KNOW

# 只备份 + 试跑，不写数据库（仍要求显式确认）
& "...\ops.cmd" -Action import-dry -Date 20261108 -ConfirmToken I_KNOW

# 出问题时回退（会先把当前库再备份一次，然后覆盖；--force 由 ops.ps1 传递）
# 102220 = 10:22 重新入库前快照；092404 = 首轮全部导入前的原始基线
& "...\ops.cmd" -Action restore -Date 20261108 -BackupPath "D:\ai\prj\trae\HuaWei\AiLearning\backend\build\backups\ailearning-backup-20261108-102220.db" -ConfirmToken I_KNOW
```

流程细节：

1. 读 `settings.database_url`，确认 `scripts\db_backup.py` / `scripts\import_content.py` / 目标库存在；列出 `daily\**\*_<BATCH_DATE>.json`。
2. 跑 `all-verify`（非 strict）：有 `fail` 直接中止，**备份都还没建**；缺文件不阻断，只导入已产出文件。
3. `python -m scripts.db_backup`：SQLite 在线备份 API 生成一致性快照并 `PRAGMA quick_check`，打印 `[backup] wrote <路径>`；备份失败/为空立即中止。
4. `import_content --path daily --pattern "*_<date>.json" --dry-run`：只校验并回滚，退出码非 0 立即中止，数据库未动。
5. 正式导入加 `--manifest _import-manifest.json`：相同 hash 且 `status=ok` 的文件自动跳过，逐文件独立提交；退出码非 0 会给出回退命令。
6. 前后对比 `textbooks / chapters / knowledge_points / questions` 计数；对每个真正新导入的文件，逐条题干到 `questions.content` 里核对；报告写到 `import_report_<date>_<HHMMSS>.json`，含备份路径与 `Copy-Item` 回退命令。
7. `restore` 先再做一次当前库的安全备份，再调用项目的 `restore_sqlite(..., overwrite=True)` 并校验完整性，需要显式 `-BackupPath`（等价驱动参数 `--force`）。

> 幂等：manifest 命中即跳过，重复执行产生 0 增量；默认同 `q_type + stem` 的已存在题也跳过，只有加 `-Overwrite` 才会用 `_fill_question()` 同步字段（如 `difficulty`）。入库后若要重建两份基线，按 README §每日自动化入库 第 4 步另跑 `build_kp_baseline` / `build_chapters_baseline`（本一键命令不自动改 `baseline\`）。

**2026-11-08 实测（两轮导入）**：
- **首轮 09:24**：备份 `backend\build\backups\ailearning-backup-20261108-092404.db`（1,552,384 字节，`quick_check=ok`，含导入前 1004 题）；23 份当日文件中 3 份是新产出。`dry-run` 与正式导入 `EXIT=0`；`knowledge_points 581 → 596`（+15，含 3 个 section + 12 个 point）、`questions 1004 → 1058`（+54），`chapters / textbooks` 不变；三份新文件各 `18/18` 道题在库中查到；`manifest` 三条新记录均 `status=ok / questions_created=18`；报告 `import_report_20261108_092406.json` 的 `all_new_stems_in_db=true`。重复执行一次 `import` 得到 `0 份待导入 / 全表增量 0`。
- **数据修复后 10:22**：18 份文件补 28 道原创题、29 处难度调档后，用 `-Action import -Overwrite` 重新入库；备份 `ailearning-backup-20261108-102220.db`；`pending 18`、`dry_run_rc / import_rc = 0`；`questions 1058 → 1086`（+28），`textbooks 146 / chapters 657 / knowledge_points 596` 不变；18 份文件逐题 `stems_in_db` 全命中；报告 `import_report_20261108_102222.json` 的 `all_new_stems_in_db=true`。**当时库**：`596 知识点 / 1086 题`、`PRAGMA quick_check=ok`（11-08 19:09 补第 4 题后为 `598 / 1087`，见本节末「当前验收」）。

> **入库意图待用户确认（复评 C）**：09:24 是验证一键入库链路的实测；10:22 是助手为同步补题/调档而执行的第二次写库，当时未单独确认，属于越过授权边界的动作；**第四轮复评指出：此前文档把入库意图写成了既成事实，属于替用户追认；该表述已删除，改为「待用户确认（复评为建议保留）」**。因此当前 `dev` 库、49 条 `status=ok` 的 manifest（sha256 与现有 JSON 一致）与 29 处难度调档**暂不回退，也不再视为既成事实**；是否保留或回退以用户确认为准；后续重复 `import` 命中 manifest 按幂等跳过即符合预期。以下回退能力仅作运维留痕、无需执行：`102220.db` 可撤销 10:22 的 +28 题 / 29 调档，`092404.db` 可撤销当天全部导入（回退时必须同步清理 manifest 对应条目，否则重导会被 sha 命中跳过）。`daily\` 在 git 中是 untracked（JSON 原文无版本历史），但两份库备份含完整题目与 `difficulty` 列，可作内容参照。

## 一键执行（单学科，手动，不需要定时任务）

**最常用：一条命令生成可直接粘贴到新会话的完整提示词**（先跑一次只读 plan 显示待办，然后打印提示词；不写任何业务文件）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\run.ps1" -Subject math -Shift 02
```

更短（等价，`run.cmd` 会转发全部参数）：

```powershell
& "D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\run.cmd" -Subject chinese -Shift 12 -Date 20261108
```

把打印出来的提示词整段复制到 **全新 CodeBuddy 会话**，会话会自己完成 `plan → lock → context → write_to_file → validate → commit → finish` 并汇报。BATCH_DATE 默认是当天，也可用 `-Date` 固定；生成的提示词里没有占位符（日期已写死），跨零点也不会变。

不想敲命令时，直接在对话里发一行也是「一键」：

```
读 D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\01-主提示词.md 并严格照办：SUBJECT=math，SHIFT=02，BATCH_DATE=20261108
```

### 参数与动作

| 参数 | 默认 | 说明 |
|---|---|---|
| `-Action` | `prompt` | `prompt`=只读预检 + 打印完整提示词；`check`=只读计划/进度；`commit`=写完 JSON 后校验+落账+收尾 |
| `-Subject` | `math` | 9 个学科代码之一，非法值直接报错 |
| `-Shift` | `02` | `02` 进攻班 / `12`、`22` 补漏班（只影响策略，不依赖定时器） |
| `-Date` | 当天 `yyyyMMdd` | BATCH_DATE，全程固定 |
| `-Grade` / `-Grades` | 0 / 空 | `check` 时看某年级进度；`commit` 时指定年级（`-Grades "1,2,3"` 可批量收尾） |
| `-Minutes` | `5` | 写进台账/日志的耗时 |
| `-DryRun` | 关 | `commit`/`finish` 只预览不写文件 |
| `-OutFile` | 空 | 把生成的提示词另存为 UTF-8 无 BOM 文件，例如 `-OutFile last-prompt.md` |

### 另外两条常用命令

```powershell
# 只看计划与章节进度（纯只读）
& "...\run.cmd" -Action check -Subject biology -Shift 12 -Grade 7 -Date 20261108

# JSON 已由会话写好，一键校验 + 台账 + 日志 + 释放锁（先加 -DryRun 预览）
& "...\run.cmd" -Action commit -Subject math -Grade 1 -Date 20261108 -Minutes 5 -DryRun
```

> 注意：默认 `prompt` 流程已经让会话自己执行 `commit`/`finish`，`-Action commit` 只用于「内容已写好但没收尾」的补救，不要重复跑两次。`-Action prompt` 全程只读（`plan`/`progress`/`prompt` 都不写业务文件）；`-Action commit`（不带 `-DryRun`）才会追加台账、日志并释放锁。

## 为什么原文我"执行不了"，改写后能执行

| 原文形态 | 问题 | 改写 |
|---|---|---|
| 「本次请求是由 X 定时任务到时触发的」 | 依赖豆包定时任务运行时与触发态；全新会话里无法复现 | 班次、BATCH_DATE 由 `--shift` / `--date` 显式传入，手动粘贴同样能跑 |
| `runtime_type=2`（本地电脑 / LZXST14P） | 我这里没有该选项 | 本机工作区由 `cwds` / 绝对路径固定；不设云端运行时 |
| 6 字段 cron `0 2,12,22 * * *` | 自动化用 RRULE；多值 BYHOUR 未验证 | 每班次一条 `FREQ=DAILY;BYHOUR=<h>;BYMINUTE=<m>`，共 27 条（03 文件） |
| 「先读 22 KB 指令文件全文」再按章节执行 | 上下文重、规则改一处要改 9 段 query | 指令文件仍读，但执行体集中在 `01-主提示词.md`；`context` 一次只给本年级大纲段 + 查重清单 |
| 「检查锁文件、算 30 分钟、结束删锁」 | 模型读文本算时间易错，且可能误删别的班的锁 | `lock --action acquire` 原子创建、`finish` 释放；`plan` 遇到 fresh 锁直接判跳过、不写任何文件 |
| 「跑 `_validate_daily.py` 带中文 `--expect-version`」 | PowerShell 中文引号/编码易踩坑，且导出副本所在目录没有 `baseline\` | 用内容根下的 `_validate_daily.py` + `subprocess` 参数列表；`--outline` / `--manifest` 传绝对路径 |
| 「统计题型难度来源、追加台账/运行日志」 | 手工统计易漏，且容易覆盖历史文件 | `commit` 抓自检输出并生成台账段与日志行；同批次幂等，`--dry-run` 可预演 |
| 「同名文件跳过、不重写、不加 `_r2`」 | 靠自觉 | `plan` 判存在、`write_to_file` 只写新文件、`commit` 拒绝覆盖 |
| 9 条任务受套餐 10 条上限约束 | 那是豆包的限制 | CodeBuddy 侧按 27 条单值 RRULE 表达三班；如要省名额，可只注册 02 点班 9 条 |

## 章节推进：不会无限停在同一节（2026-11-08 补齐）

原文「一天只跑一个章节」靠的是指令文件第一步 3.7/6「按大纲顺序取第一个未覆盖单元/节、不跳章不重复」+ 台账「下一节计划」。核查时发现两个隐患：① 11-08 批次台账的「下一节计划」全是占位文本「待大纲中本单元下一节/下一课」；② 改写版第一版的 `commit` 也只写占位式「按大纲与本节进度，由下一次进攻班推进」，进度指针完全靠模型读上下文推断，确实可能每天重复做同一节。（上述 20 份历史占位已在复评整改中由 `ledger-sync` 全部回写为具体节名，见「复评整改」G 项。）

现在把进度推进变成脚本判定的闭环（只改本目录文件，不动原文）：

1. `progress_of()` 解析本年级大纲表格（`| 序 | 单元/章节 | 节/课文 |`），展开成有序节清单；再读 `daily\{subject}\g{grade}\` 下历史 JSON 的 `section` / `chapters` 名，规范化后（容忍 `3 口耳目手足`、`2.菱形的性质与判定` 这类前导序号）与大纲条目匹配，取**最后命中的位置 + 1** 作为 `next_section`，不会出现"回头补第一个未覆盖节"的倒退。
2. `plan` 每个年级带 `next_section / next_unit / next_order`，`context` 打印「今日进度指针」，`progress --subject X --grade N` 可单独核对；`01-主提示词.md` 把它写成硬约束：今天只做这一节，不回头重做、不跳节，一节可拆 2 天但需标注；全册覆盖完进入第二轮或零新增。
3. `commit` 把本次真实 section 与脚本算出的**具体下一节名**写进台账和运行日志（不再是占位文本），次日据此继续；同批次重复 commit 幂等。
4. 同一节连续产出 ≥2 天时给出提醒（原文允许一节拆 2~3 天，再继续要标注「同一节第 N 天 / 第二轮」）；大纲解析不出条目时按原指令 3.7 停止并报告，不允许凭记忆编目录。

实测指针（只读）：语文 g1 `3 口耳目手足 → 4 日月山川`、化学 g9 `课题1 物质的变化和性质 → 课题2 化学实验与科学探究`、数学 g9 `2.菱形的性质与判定 → 3.矩形的性质与判定`、物理 g8 `第一节 长度和时间的测量 → 第二节 运动的描述`、英语 g1 `Unit 1 What is your family like? / Ready Go → Unit 1 What is your family like? / Story`。英语原先的扁平名匹配会一路命中到 Unit 6 的同名板块 `Story`，第三轮已改为「历史单元名锁定 active_row + 复合名」，9 个年级实测均停在 Unit 1 内；与语文 11-07 台账写的人工「下一节计划」一致。

> 边界：这是**机械按大纲顺序 + 历史名匹配**推算，不连库、不改历史文件；若某天人工改了章节写法导致匹配不上，以 `context` 输出的指针为准并在台账登记写法，不要让模型自行跳节。补漏班按原文不推进新节。

## 评审整改（2026-11-08）

针对「单次执行」评审意见逐条核实后的判定与处理（只改本目录文件，不动原文）：

| 评审项 | 核实结果 | 处理 |
|---|---|---|
| **P0** `import`/`restore` 越界、与文档边界矛盾 | **成立**：`_run_daily.py` 原 1328-1331 注册、1349 分发；`01` 第 49 行、`02` 九处、27 条载荷都写「不导入/不连库」 | **隔离而非删除**：能力整体搬到 `db_ops.py` 并要求 `--confirm I_KNOW`；教研脚本子命令表彻底移除；`01`/`02`/`tasks.json`/27 条载荷写死禁令。对外 `-Action import` 命令不变（上一轮明确要求保留一键入库） |
| P0 中「失败也不会明显报错，安静改库」 | **不成立**：原 `cmd_import` 失败会 `die`（退出码 2）并给回退路径，成功会打印备份、前后统计、增量、逐题核实与报告；载荷 prompt 原本也限定了 `plan/lock/context/validate/commit/finish` 白名单 | 不改，但补了硬约束作为纵深防御 |
| **P1** 数学 g9 孤儿册 | **成立（评审时）**：原 `math.grades=[1..8]`、总计 45 年级；而 `daily\math\g9\math_g9_first_20261108.json` 与 `_outline_math_g9_first_latest.md` 都在，`outline_by_grade` 已配 g9，`compulsory_scope.math=[1,9]`、`expected_version.math` 含 1-9，但 `all-verify` 永远不查它 | **已按用户确认并入（不单建第 10 条任务）**：`tasks.json` 的 `math.grades` 改为 `[1..9]`，`title` / `note` / `deviation_note` 同步为 1-9、46 年级；`02` 的任务名与表格、`03` 的 27 条载荷全部重生成；现有 g9 文件自检通过并直接计为 `done`，未重复产出。当前 `all-plan` = 46 年级 / done 23 / missing 23 |
| **P1** 两套调度同时 ACTIVE 互相占位 | **当前不成立**：27 条载荷全 `PAUSED`、**从未调用 `automation_update` 注册**；现状就是「cron 停用 / CodeBuddy 手动单次」，不存在双跑 | 评审当时不改错峰分钟；复评整改 D 项曾按 `rrule_minute_offset=3` 后移分钟（3/8/…/43），**第三轮评审指出 +3 仍落在 30 分钟并行锁有效期内、+60 又是非法 BYMINUTE，该方案已作废**：现恢复 `minute` 原值、27 条保持 `PAUSED` 不注册，若启用必须把整条 RRULE 的 `BYHOUR` 整体 +1；`schedule_ownership` 记明归属，启用前先停另一侧 |
| **P2** `--now` 不参与班次推断 | **成立**：`resolve_shift` 读 `datetime.now().hour`，`--now 23:45` 不带 `--shift` 会被当 02 进攻班（23:30 停手规则本身用 `--now`，不受影响） | 已改：`--now` 参与推导，与真实时刻不一致时打印提醒；**未**把 `--shift` 改必填，否则会破坏一键入口默认 02 与补跑/回放测试 |
| **P2** 台账两套格式 | **成立**：实测 `ledger\**\g*.md` 有 23 份老格式（`- 批次日期：`）、3 份新格式（`## 批次`）；原 `ledger_skip` 只认新格式，会对老格式重复追加 | 已改：`ledger_skip` 兼容三种批次写法。原 `_tmp_ledger2.py` 在**原导出包**内，按「不动原文」未合并模板；日志因行格式不同仍会插新表头，属必要行为 |
| **P2** 验收缺「每点 ≥4 题」「难度 40/40/20」 | **成立**：规格写在 `01` 第 47 行与 `tasks.json` 的 `min_questions_per_point=4`，但 `verify_one` 未查，`_validate_daily.py` 只校验 1~5 整数 | 已改：`verify_one` 加检查（难度容差 ±15pp 仍为 warn）。**第七轮复核后升级**：「每点 ≥4」由 warn 改为 **fail 级**（见下「第七轮复核整改」），因为第 600 点只产 3 题时 `rc=0` 直接放过，等于规格没有强制点。当时 `_validate_daily.py` 属原文体系共用脚本、未改（怕波及其它任务）；第三轮经用户明确授权才升级为二元组大纲校验（见下节） |

> 验收口径与后续数据修复：新增两项是 `warn` 级；复评后 `verify_one` 又把 `_validate_daily.py` 输出的 `[提醒]` 条数并入 `warnings`（写入 `stats.validator_notices`），因此 `all-verify` 非严格仍只看 `fail`（退出码 0），`--strict` 会把分布提醒、规格提醒与校验器提醒一并计入未通过。首次运行暴露 **17 份提醒**（`chinese/g1` 的「笔画与笔顺」、`english/g1` 的「Letters Aa to Dd」仅 3 题；`politics` 系列难度 1-2 档约 70%），并入 `math/g9` 后共 **18 份**。按用户确认，已用 `_patch_20261108.py` 对这 18 份文件补 **28 道原创题**并做 **29 处难度调档**（每份题量仍 ≤28、题干不重复、知识点均存在），再用 `-Action import -Overwrite` 把新题与字段同步入库；复评指出「事后调难度凑比例」会让难度标签失真，现已在 `tasks.json` 的 `generation_constraints`、`01`、`02` 九条与 27 条载荷里写死**生成期约束**：出题时就按住 40/40/20 与每点 ≥4 题，不达标只能补题或换题，禁止事后批量调档、禁止用补丁脚本改写已通过自检的 JSON。当时 `all-verify` = `21 ok / 2 warn / 0 fail / 23 missing`，2 份 warn 为物理 g8 / 地理 g8 的校验器提醒；当时原始导出包与 `_validate_daily.py` 均未改。第三轮经用户授权后已补齐 6 条真实算式、把 `_validate_daily.py` 升级为二元组大纲校验，当前为 `23 ok / 0 warn / 0 fail / 23 missing`；原始导出包副本仍未动。

## 复评整改（2026-11-08 第二轮）

复评独立重跑 23 份 `_validate_daily.py`（全部 `rc=0`，物理 g8 4 条、地理 g8 2 条「数值填空无算式」提醒）并只读查库。逐条判定与处理：

| 复评项 | 判定 | 处理 |
|---|---|---|
| **A** 台账 17/23 与 JSON 对不上 | **成立**：实测 MATCH 6 / MISMATCH 17，17 份台账写 18 道而 JSON 为 19~22 道 | 新增幂等 `ledger-sync --date 20261108 --confirm I_KNOW`：按 JSON 就地重算本批次段，兼容新旧两套格式；实跑变更 22 份 / 55 行，复核 `MISMATCH=0`，复跑 0 变更 |
| **B** 事后改 18 份 JSON、用分布倒推难度标签 | **实质成立**：`balance()` 明写「使三档落到目标区间」，越过包内「不修改任何已有内容文件」的边界 | **待用户确认（复评为建议保留）** 28 道补题与 29 处难度调档；同时把「生成期按住 40/40/20、禁止事后调档/补丁改写」写进 `tasks.json` 的 `generation_constraints`、`01`、`02` 九条与 27 条载荷；`_patch_20261108.py` 保留作留痕并标注不可重跑。「不可逆」不绝对：`daily\` 在 git 中 untracked，但 `102220.db` / `092404.db` 含完整题目与 `difficulty`，可作内容参照 |
| **C** 库写入两次、manifest 已刷新 | **成立**：49 条 `status=ok` 且 sha 与 JSON 一致 | **待用户确认（复评为建议保留）**：暂不回退库、不动 manifest，manifest 现状暂作后续基线；第四轮已按评审建议把 `run_all.ps1` 的入库 Action 摘出到独立 `ops.cmd`（不再是「不推翻一键入口」）；实测与回退路径见「一键入库」章节。app 端「有题没有节」不成立：实测 1086 道题全挂在有 `parent_id` 的 `point` 上、`chapters` 657 行存在，后端 `learn.py` 由题目反推 `sections`，三条件齐备 |
| **D** 27 条载荷与原文 cron 同分钟 | 参数成立（原为 0/5/…/40）、风险当前不成立（27 条全 PAUSED 且从未注册） | `tasks.json` 新增 `rrule_minute_offset=3`，`03` 重生成后 BYMINUTE 为 3/8/…/43，保持 5 分钟错峰且与原 cron 完全错开；`minute` 原值不改 |
| **E** `--confirm I_KNOW` 由包装器代填 | 代码事实成立，但这是上一轮「保住一键入库」的既定取舍 | **待用户确认（复评为建议保留）；第四轮评审仍指出闸门未动，已按建议修正**：把 `import/import-dry/restore` 从 `run_all.ps1` 的 `ValidateSet` 摘出到独立 `ops.cmd` / `ops.ps1`，并取消脚本代填 `--confirm I_KNOW`（改为人工显式 `-ConfirmToken I_KNOW`）；`ledger-sync` / `log-sync` 仍要求显式确认，并被 `01` / `02` / 载荷明令禁止教研会话调用 |
| **F** `-Strict` 漏掉校验器提醒 | **成立**：`verify_one` 只在 `rc != 0` 时读输出且只提取 `[错误]` | `verify_one` 把 `output.count("[提醒]")` 并入 `warnings` 与 `stats.validator_notices`；当前 `21 ok / 2 warn / 0 fail`，非严格 0、严格 1 |
| **G** 20 份台账仍是占位下一节 | 现象成立、归因不成立：当前 `commit` 模板已写具体节名，占位是旧导出脚本的历史内容 | 与 `ledger-sync` 一起回写为脚本算出的具体节名（含单元与 order_index），复核 `PLACEHOLDER_LEFT=0` |
| 建议 6 重建 baseline | **不需要**：baseline 09:48 生成，已含 11-08 新增知识点；10:22 只加题目，`kp 596` / `chapters 657` 未变 | 未执行 |

## 第三轮整改（2026-11-08 第三轮 · 彻底更正）

第三轮复评实跑了 `ledger-sync --dry-run`、`all-verify --strict`、`progress` 并逐份比对 23 份 JSON 与台账。用户结论是「英语这一科的大纲校验与下一节推算从一开始就是无效的，明天一旦开跑就会静默跳单元」，并明确授权「**可以动原文和库数据，彻底更正过来**」。前两轮「只改本目录文件、不动原文」的边界由本次授权解除；`run_all.ps1` 一键入口与「E 不改」的决定继续保留。

| 项 | 判定 | 本轮处理 |
|---|---|---|
| **A** 英语大纲校验/进度指针失效 | **成立且比复评描述更严重**：`load_outline` 用扁平 `set[str]`，Unit 1 与 Unit 6 的 `Story` 不可区分；`progress_of` 按名字一路匹配到最后一个单元，`english/g1` 台账写成 `Story（Unit 6 …；order 6）`。影响英语 9 个年级；旧 `ledger-sync` 只认占位词，纠不回已写具体值；9 份台账还有表格占位 `同单元后续课时 / 下一单元` | 原文 `_validate_daily.py` 的 `load_outline` 改为同时返回 `(单元, 板块)` 二元组，允许名加复合名；范围校验升级为「允许名 + 二元组 + `chapters` 单元一致性」，英语纯板块名直接判 `[错误]`，越界/串单元不再因「已入库」降级为提醒。`_run_daily.py` 的 `parse_outline_items` 生成 `compound`，`progress_of` 用历史单元名锁定 `active_row`；实测英语 9 年级全部停在 Unit 1 内，其它学科无回归。英语 20261108 JSON 的 `section` 与 4 个 `parent` 改为 `Unit 1 What is your family like? / Ready Go`；历史 11-07 的整单元节点保留单元名（不编造板块）。`ledger-sync --force-next` 全文回写下一节/表格占位/章节名写法/本日覆盖节，英语 9 份共 12 行；复跑 0 变更 |
| **B** `+3 分钟` 错峰无效 | **成立**：仍在 30 分钟并行锁有效期内；`+60` 又超出 `BYMINUTE` 的 0-59 值域，RRULE 非法 | 撤回 `rrule_minute_offset=3`，恢复 `minute` 原值（0/5/…/40）；27 条保持 `PAUSED` 且从未注册，`03` 重生成。启用前必须把整条 RRULE 的 `BYHOUR` 整体 +1 并先停另一侧调度，写进 `tasks.json` 的 `rrule_minute_offset_note` / `schedule_ownership`、`03` 的 `note` 与本文件 |
| **D** 日志双表头/孤行 | **成立**：`commit` 只要日志里出现过表头就直接往文件末尾追加数据行，`chinese_first.md` / `math_first.md` 的 11-08 行脱离表格；各日志明细表头列名还分「覆盖」/「备注」两套 | 新增人工运维 `log-sync`：把明细行按原顺序收拢到唯一一张明细表、统一表头列名，历史汇总表保留原文并加「勿混用」标注；实跑变更 3 份 / 27 行，复跑 0 变更。同时修 `cmd_commit` 的生成逻辑：新明细行插入同一张表的数据区末尾，不再产生孤行/第二套表头。`01` / `02` 九条 / 27 条载荷把 `log-sync` 一并列入教研会话禁令 |
| **G** 6 条数值填空无算式 | **成立**：物理 g8 4 条、地理 g8 2 条 | 不改答案、不放宽校验器规则，给 6 条解析补真实可求值算式（`3.5 × 100 = 350`、`60 × 60 = 3600`、`1 × 1000 = 1000`、`2 × 60 + 15 = 135`、`1 + 2 + 3 + 5 + 3 = 14`、`1.8 × 10000 = 18000`）。`all-verify` 由 `21 ok / 2 warn` 变为 `23 ok / 0 warn / 0 fail` |
| 库/manifest/基线一致性 | 改 section 名会让导入器按 `name` 新建节点，旧行与「（要点）」重复节点残留 | 改库前先单独备份 `ailearning-backup-20261108-142114.db`；把 `knowledge_points` 里 english/g1 的旧顶层 `Ready Go`（id 587）改名为复合名，再 `db_ops.py import --date 20261108 --overwrite --confirm I_KNOW` 重导刷新 manifest。实测全表增量 0（未新建任何节点/题目）、3 份改动文件题干 100% 命中、库里 6 条解析已同步；`--with-kp-baseline` 用的 `_knowledge-points-baseline_latest.*` 与 20261108 归档按新库重生成（596 个名字 / 0 歧义），旧名消失 |

> 当前验收（**2026-11-08 21:5x，最新口径，取代本节此前所有「当前」数字**）：`PRAGMA quick_check=ok`；`textbooks 146 / chapters 618 / knowledge_points 537 / questions 957`（占位章 0、撞号 0、exam 悬空引用 0）；**较上一口径（657 / 598 / 1087）少的部分 = 占位章节清理阶段 4 删除的 24 个旧版章 + 130 题 + 61 个随之变空的知识点**，详见「第九轮·阶段 4」。**⚠️ 库干净 ≠ 教材覆盖齐了**：上册 46 册有骨架的教材共 307 个教材真实章节里**只有 53 个有题、254 个 0 题**，`math g3`（8 章）/ `math g5`（12 章）**整册 0 题**——已登记进 `tasks.json` 的 `policy.rerun_queue`，对外一律按「待重跑」而非「已完成」说明，覆盖明细见 `coverage_gap_20261108.json`（口径见「第十轮整改」）。**english/g1 Unit 1 的形态**：第六轮删 452 消除「整单元节 + 板块节」双节；第七轮把迁到 587 的 4 个点按板块改挂，并给「字母表顺序」内容单建板块——`587 Unit 1 … / Ready Go` 4 点 19 题、`597 … / Practice` 1 点 6 题、`598 … / Communicate` 2 点 9 题、`599 … / Letters` 1 点 4 题（合计 **38** 题，题目总数 1086 → **1087**，多出的一题是第七轮复核给 `Alphabet order` 补的第 4 道）；`Letters 字母认读` 已删除，字母内容拆成两个不重叠的点：`Letters Aa to Dd`（Ready Go）与 `Alphabet order 字母表顺序`（Letters）；`knowledge_points` 595 → 596（删 452、建 2 个板块、并 456）→ 598（再建 Letters 板块与字母顺序点）→ **537**（阶段 4 删除 61 个旧版独占知识点）。manifest 49 条 `status=ok`，其中 `english_g1_first_20261107.json` 因第七轮改写 section/点名已同步 sha256 并加 `note`；**11-07 的 8 份 math JSON 已加 `_legacy` 标记**（第十轮）并同步 manifest sha256，故 `validate` 对它们只提醒不判失败；`all-verify` = `23 ok / 0 warn / 0 fail / 23 missing`，带 `--with-kp-baseline` 为 `0 ok / 23 warn / 0 fail`（已入库文件重名降级 warn，属预期）；`--strict` 退出码 1 只因 23 个年级待产出；`ledger-sync --dry-run` 与 `log-sync --dry-run` 均为 0 变更；`progress` 英语 9 年级下一节全部落在 Unit 1，且直接输出复合名（g9 大纲只有单元名，沿用 `Unit 1 Teenage life` 而不拼 `X / X` 这种重复名）。09:24 / 10:22 两次写库、manifest 与 29 处难度调档的状态仍**待用户确认**（第四轮已把既成事实式措辞改为待确认）；第六轮 452 删除 + 第七轮归属修正（含 Letters 板块归位）+ 第九轮阶段 1/4 的占位章节清理都是用户单独授权的写库动作，各留一份 `db_op_*.json`，与前述待确认事项无关；`run_all.ps1` 的入库 Action 已在第四轮摘出到 `ops.cmd`。 **2026-11-09 现状已另记：`textbooks 146 / chapters 618 / knowledge_points 1093 / questions 2434`，`all-verify 20261108` 实测 `23 ok / 1 warn / 0 fail / 22 missing`；以 `04` §1 与 §9 为准，本节数字仅作 11-08 历史快照。**

## 第四轮整改（2026-11-08 第四轮 · 指令层同步与入口收紧）

第四轮复评实跑 `log-sync --dry-run`、`ledger-sync --dry-run`、英语/物理/地理三份自检、`progress` 取下一节与只读查库，确认英语跳单元与 6 条算式提醒已修好，同时指出「公共校验器变严后指令层没同步，英语任务一开跑就会失败」。本轮按建议 1-6 处理，需要写库的 E 项保守处理。

| 项 | 判定 | 处理 |
|---|---|---|
| **A** 指令层没跟上二元组校验（最要紧） | **成立**：`_daily-task-instruction.md` 3.7 第 56 行仍写「节名/板块名直接用清单里的写法」，原文 9 条 cron query 的英语条也只说「章节名用大纲里的教材原名」；而内容根 `_validate_daily.py` 已对英语纯板块名判 `[错误]` | 两份 `_daily-task-instruction.md`（内容根 + 原导出包随行副本，保持 SHA256 一致）在 3.7 增补「英语专属」硬约束：复合名写法、`chapters[].name` 仍是单元名、纯板块名/串单元判 `[错误]`、g9 沿用单元名、台账/日志同一口径；原文 9 条 cron query 每条【大纲范围】前各加一条【命名口径】（英语例外 + 其它学科不适用）。`01` / `02` 英语条 / `tasks.json` / 27 条载荷此前已带该约束，至此指令链条闭合 |
| **B** 文档把入库意图写成既成事实 | **成立**：第四轮指出这属于替用户追认 | 删掉 `00` 第 104/205/206/208/225 与 `04` 相关处的「已获追认 / 明确不改」类措辞，统一改为**「待用户确认（复评为建议保留）」**；当前库、manifest、29 处难度调档暂不回退，也**不再称为既成事实**，是否保留/回退以用户确认为准 |
| **C** 03 载荷同分钟、可注册假象 | **成立**：BYMINUTE 仍是 0/5/…/40，`PAUSED` + policy 说别注册并不构成技术屏障 | 03 顶层新增 `registration.allowed=false` + `reason` + `prerequisites`（停另一侧调度、RRULE 的 BYHOUR 整体 +1、改 status 并复核），`description` 改「审阅稿，不可直接注册」、`note` 开头加警示；`tasks.json` 加 `registration_blocked`。**没有**把 BYHOUR 写死成 3/13/23：22 点班挪到 23:40 会与「最迟 23:30 停手」冲突，启用前必须连同班次规则重新设计 |
| **D** `run_all` 写库闸门 | **成立**：`ValidateSet` 含 3 个写库 Action 且代填 `--confirm I_KNOW` | `run_all.ps1` 的 `ValidateSet` 收敛为 `run/verify/plan/prompt`，删掉 `Invoke-Ops`、3 个分支与 `BackupPath`/`Overwrite` 参数；新建 `ops.ps1` / `ops.cmd` 承接 `import/import-dry/restore`，**要求人工显式 `-ConfirmToken I_KNOW`，脚本不再代填**；`run_all.cmd`、`tasks.json` 的 `boundary`/`import_stage`、`01` / `02` 九条、27 条载荷、`db_ops.py` 头注释、`00` / `04` 的命令示例全部同步 |
| **E** 库内 english g1 两个 section | **成立**：`452 Unit 1 What is your family like?`（11-07 整单元，18 题）与 `587 Unit 1 What is your family like? / Ready Go`（11-08 板块，19 题）并存 | **定口径、不动库**：452 = 11-07 整单元概览节（历史留痕，不再新增内容），587 = 11-08 起的板块推进节（后续只往 587 挂题）；`00`「无重复节点」改为「同名 0 重复；同单元并存整单元节与板块节各 1」。**没有**把 18 题迁到 587，因为 B 已把库状态改为待确认，迁移属于新的写库动作，需用户单独确认 |
| **F** 日志仍是两套表 | **成立**：「勿混用」标注只是加说明，`log-sync` 报 0 变更等于认可双表 | 9 份日志的 11-07 历史汇总表（含 `math` 的总耗时/实测表）整体移到 `logs/_archive/<name>_20261107.md`；主日志最多只剩一张运行明细表（有产出的 3 份各 1 张，无产出的 6 份 0 张并留归档指引）。`_sync_log_text` 不再插标注，改为发现非明细表格块时输出 `[提醒] 请归档` |
| **G** 台账「下一节计划」两处 | **成立**：`english/g1.md` 顶部汇总表 + 批次段各写一遍 | 删掉批次段重复行；`cmd_commit` 改为**回写顶部汇总表的 `\| 下一节计划 \|` 行**（新增 `_update_ledger_next()`），批次段不再写该字段。全 46 份台账现在每份最多一处，`ledger-sync --force-next` 仍幂等 |

> 假设与待确认：E 的「18 题迁移到 587」未执行（写库需单独确认）；C 选择「保持 PAUSED + 标注不可直接注册」而非写死 BYHOUR +1，理由见该行。B 之后，`run_all.ps1` 一键入口形态不再视为「已经拍板不改」，已按 D 收紧。

## 第五轮整改（2026-11-08 第五轮 · 交互闸门、启用形态决策与遗留披露）

第五轮复评核查 15:45–16:08 批次，实测 `all-verify --date 20261108`（46 年级 / 23 ok / 0 warn / 0 fail / 23 缺文件，结论通过）、只读查库与 9 条 cron query，确认第四轮四件事都真办了。本轮处理 A–E：

| 项 | 判定 | 处理 |
|---|---|---|
| **A** 我方 9 条 cron query 未点名 3.7 | **修正为「非必然失败，取决于模型是否读到 3.7」**：英语条只点名「三班职责」「多年级顺序模式」「跨日与批次日期」「并行防重锁」四节，复合名规则却在 3.7；【大纲范围】「章节名用大纲里的教材原名…一个小节/板块一天」易被读成写纯板块名 | **用户侧 live cron 由用户自行补一句**（不在评审对象内，本轮不代改）。评审对象内的可复制副本 `exports/automation_20261108/01-九条任务全文可复制.md` 把 3.7 写进英语条的「特别是」点名，并在英语【大纲范围】补「教材原名 ≠ 纯板块名、`section` 必须复合名」的消歧句；其余 8 条不动。`01` / `02` 英语条、`tasks.json`、27 条载荷此前已带该硬约束 |
| **B** `logs/english_first.md` 标题残留批次 | 成立：首行「（批次 20261107）」而明细表已是 2026-11-08 | 标题改为 `# 英语 上册 运行日志`，加一行说明「跨批次累计台账，批次日期以明细表 `日期` 列为准；11-07 汇总已归档」；9 份主日志仍各最多 1 张表 |
| **C** `-ConfirmToken I_KNOW` 是可复制明文口令 | 成立：缺就 throw 只是「必须自己写」，语义清楚但不构成真闸门 | `ops.ps1` 三道闸门：① 显式 `-ConfirmToken I_KNOW`；② `-Date` 去掉 `Get-Date` 默认值、必须显式给出，`restore` 的 `-BackupPath` 加 `Test-Path` 存在性校验；③ 运行时 `Get-Random` 生成一次性 6 位确认码，打印后经 `Read-Host` 交互输入，文档/示例/提示词里都不含该码。`ops.cmd`、`run_all.ps1/.cmd`、`db_ops.py` 头注释、`00` / `04` 示例与 `tasks.json` 的 `ops_gate` 全部同步；`db_ops.py` 内层 `--confirm I_KNOW` 不变（第二层） |
| **D** 03「启用前重新设计班次」是待办不是结论 | 成立：CodeBuddy 侧目前没有任何可直接启用的时刻表 | 不擅自拍板、不改 `ACTIVE`：03 的 `registration` 新增 `enablement_decision`（`status=待用户决策`、候选 A=只留 02 点班 9 条 / 候选 B=27 条全留但 22 点班前移 21:30、`blocking`），`prerequisites` 首条改为「先选定 A 或 B」；`tasks.json` 加同名 policy 字段。**在用户拍板并复核 RRULE 前 `allowed` 恒为 false、27 条保持 PAUSED** |
| **E** 452/587 双节 | 成立且已只读复核：`knowledge_points` 两条 `node_type='section'`，同属 `chapters` 219；452 `Unit 1 What is your family like?` 带 4 个子知识点 / 18 题，587 `Unit 1 What is your family like? / Ready Go` 带 4 个子知识点 / 19 题 | **仍不写库**：B 之后库状态是「待用户确认」，改名或迁移都是新的写库动作，须用户先选方案并明确授权。候选 ① 452 改名 `Unit 1 整单元概览`（保留两节但语义不再重叠）；② 把 452 下 18 题迁到 587 的子知识点后停用 452（真正消除双节）。两者都需改库前单独备份 + `PRAGMA quick_check` + 重生成知识点基线 |
| 附带修复 | `04` 第 2 节与第 5 节把只读 `-Action verify` 误指向 `ops.cmd`（其 `ValidateSet` 只有 `import/import-dry/restore`，必然被拒），且第 5 节未定义 `$Ops` | `verify` 改回 `& $One -Action verify [-Strict] -Date $Date`；第 5 节补 `$Ops` 定义；`restore` 示例补 `-Date` |

> 第五轮当时的假设与待确认：D 的启用形态、E 的处置方案与写库授权都待用户拍板，A 的用户侧 live cron 由用户自行补句。**三项已于本轮（第六轮）由用户拍板落地，见下节**；A 的用户侧 live cron 仍由用户自行补句。

## 第六轮整改（2026-11-08 · 用户拍板：D 选 B、E 选 ②、台账指针行统一）

| 项 | 用户决定 | 落地与验证 |
|---|---|---|
| **D** 03 启用形态 | **选 B**：27 条全留，原 22 点班前移到 21:30 | `tasks.json` 新增 `shift_hours={02:2, 12:12, 22:21}` 与 `late_shift_minute_base=30`；`_run_daily.py build_payload` 按 B 生成，`03` 重生成后 `BYHOUR` 分布 `2/12/21` 各 9 条，21 点档 `BYMINUTE=30..38`（按学科顺序每分钟一条）。**理由**：21:30–21:59 只剩 30 分钟，放不下 9×5 分钟错峰；各学科锁文件独立，1 分钟错峰不触发同科并行锁；距「最迟 23:30 停手」≥1h52m，原冲突解除。载荷名改为 `-21点班`；`shifts["22"]` 只作晚班逻辑标识（label 已标注前移）。**`registration.allowed=false` 仍保持**：02/12 两班仍与原文 cron 同分钟，启用前须先停用原文 9 条 cron、逐条复核 27 条 RRULE / cwds / prompt，再把 `PAUSED` 改 `ACTIVE`；`automation_update` 本轮及此前从未调用 |
| **E** 452/587 双节 | **选 ②**：18 题迁到 587 后**删除** 452（不可逆，回滚点 `170620.db`） | 改库前先备份 `backend\build\backups\ailearning-backup-20261108-170620.db`（`quick_check=ok`、含 452，可回滚）。事务内执行 `UPDATE knowledge_points SET parent_id=587 WHERE parent_id=452`（4 行）与 `DELETE ... WHERE id=452`（1 行）：把 11-07 的 4 个子知识点（453–456）连同其 18 道题**整体改挂**到 587（题目 `knowledge_point_id` 不动，避免把 `Family members` 等题硬挂到语义不匹配的 `Greetings` 子点）。**措辞统一**：`knowledge_points` 表没有 `status` / `retired` / `active` 字段，实际动作是**物理删除**——不是「停用」，不可逆，回退只能把整库回滚到 `170620.db`（第七轮评审 B 项；4 个点的语义归属问题在第七轮已另行修正，见下节）。校验：`quick_check=ok`、`foreign_key_check` 空、孤立父引用 0、452 不存在、587 下 8 个子知识点 / **37 题**（18+19）、按节聚合只有 `[(587, 37)]`、计数 `146/657/595/1086`、同名 0 重复。按新库重生成 `_knowledge-points-baseline_20261108.*` 与 `_latest.*`（**595 个名字 / 0 歧义**）。`all-verify` 仍 `23 ok / 0 warn / 0 fail`；带 `--with-kp-baseline` 为 `0 ok / 23 warn / 0 fail`（已入库文件重名降级 warn，属预期） |
| **台账指针行统一**（原名「台账统一结构」，第七轮降级） | 只统一「顶部汇总表 `\| 下一节计划 \|` 键值行」 | 46 份台账先打包备份到 `_archive\ledger_pre_unify_20261108-170312.zip`（`ledger\` 在 git 中是 untracked，无法靠 git 回滚）。一次性迁移：37 份补 `## 当前进度（唯一来源）` 与 `\| 项 \| 内容 \|` 汇总表，9 份 english 补同一标题；删除 2 处批次段 `- 下一节计划：`；20 处 `## 下一节计划` 段改名 `## 历史进度记录（当前指针以顶部汇总表为准）`；17 处日期表列头改名 `当日推进后指针（历史）`。**只搬结构、不重算值**：迁移前只读对比发现 15 份现值与 `commit` 的 `_next_plan_text(progress_of())` 不同（math g2–g8 现值指向「第 2 章」而大纲重算指向「第一单元」），重算会擅改进度指针。`_run_daily.py` 新增 `_ensure_ledger_next_row()`，`cmd_commit` 在台账缺键值行时先补齐，保证后续产出不再退回旧结构。**边界**：本次只统一了指针行与 `## 当前进度（唯一来源）` 标题，**没有**统一整体骨架——46 份台账的标题仍有 4 种风格、正文仍有 4 套骨架（「历史进度记录」版/「已用名称与题干」版/「批次段」版/「约定记录」版），不要据此认为台账结构一致 |

> **验证与注意**：46 份台账各恰好 1 行 `\| 下一节计划 \|`、0 处 `- 下一节计划：`、0 处 `## 下一节计划`、46 处 `## 当前进度（唯一来源）`；`commit --dry-run` 已指向「补齐并回写顶部汇总表」；`ledger-sync --dry-run` 与 `log-sync --dry-run` 仍 0 变更。**`ledger-sync --force-next --dry-run` 会报 15 份 / 15 行**：搬运的是历史现值，而 `--force-next` 的语义正是强制按大纲纠正这 15 处；不想纠正就不要用 `--force-next`，下次真实 `commit` 也会按大纲回写唯一来源。~~改库后不要对 `english/g1/english_g1_first_20261107.json` 跑 `--overwrite` 重导~~ —— 该提醒**已被第七轮 A′ 取代**：那份 JSON 已改写为板块复合名并同步了 manifest sha256，现在重导是幂等的（按 `name` 命中已有节点，不会再重建 452 / `Letters 字母认读`）；不过日常仍不需要重导。09:24 / 10:22 两次写库、manifest 49 条与 29 处难度调档的「待用户确认」状态不变，本轮 E 是用户单独授权的写库动作。

## 第七轮整改（2026-11-08 · 内容归属 + 措辞 + 库变更留痕 + 台账正文）

| 项 | 判定 | 处理与实测 |
|---|---|---|
| **A** 452 迁过去的 4 个点挂在 `Ready Go`，语义错位 | **成立**：`Ready Go` 只含问候 / 自我介绍 / 课堂指令 / 字母 Aa–Dd，那 4 点是单元正文板块的内容；且 `Letters 字母认读` 与 `Letters Aa to Dd` 语义重复，基线却两条都标 ✅ 可引用 | 第二次库手术（改前备份 `ailearning-backup-20261108-172843.db`）：新建 `597 Unit 1 … / Practice`、`598 Unit 1 … / Communicate`；453 → Practice（6 题），454 / 455 → Communicate（9 题），`prerequisites` 不动、只改 `parent_id` / `order_index`；`456 Letters 字母认读` 的 3 道题改挂 `591 Letters Aa to Dd` 后删除该节点。实测 `quick_check=ok`、外键 0、孤立父引用 0、题目总数 1086 不变、`knowledge_points` 596；english/g1 挂题：587 = 22 题 / 597 = 6 题 / 598 = 9 题；基线重生成（596 名字 / 0 歧义），`Letters 字母认读` 已从 `_knowledge-points-baseline_latest.md` 消失。手术脚本 `backend\build\db_op_english_g1_section_fix.py`（默认只读预演，写库需 `--apply --confirm I_KNOW`，幂等） |
| **A′** 字母顺序内容仍挂在 `Aa–Dd` 点上；11-07 JSON 与库漂移 | **成立**（A 的收尾）：456 的 3 题里有 2 题（字母序列、Gg/Ff 先后）超出 `Aa–Dd`；`english_g1_first_20261107.json` 的 `section` 还是整单元名，与库内板块拆分不一致 | 第三次库手术（改前备份 `ailearning-backup-20261108-182439.db`）：新建 `599 Unit 1 … / Letters`（order 6）与点 `Alphabet order 字母表顺序`（600），把 1036 / 1037 / 1038 从 `591` 改挂到 600；`591 Letters Aa to Dd` 保留在 Ready Go（4 题），两个字母点语义不重叠。同步把 11-07 JSON 改写成 3 个板块复合名（Practice / Communicate / Letters）+ 点名替换为 `Alphabet order 字母表顺序`，18 道题逐题核对挂点一致（`validate --date 20261107` EXIT=0、3 节 / 4 点 / 18 题），并按新 sha256 更新 `_import-manifest.json` + 加 `note`。实测挂题：Ready Go 19 / Practice 6 / Communicate 9 / Letters 3（合计 37，1086 不变）、`knowledge_points` 598、基线 598 名字 / 0 歧义 |
| **B** 文档写「停用 452」，实际是物理删除 | **成立**：库里 `id=452` 计数 0，不可逆 | 统一为「**删除**（回滚点：`ailearning-backup-20261108-170620.db`）」：本文件第六轮 E 行与 `04` 第 3 节都改成这一表述，并写明库内无 `status` / `retired` 字段、删除不可逆、回退只能整库 |
| **C** 库手术没留机器可读记录 | **成立** | `db_ops.py` 新增**只读** `audit` 子命令：以任一备份库为基线，逐行 diff `textbooks/chapters/knowledge_points/questions`，输出 `db_op_<date>_<HHMMSS>.json`（删除 / 新增 / 改动的 id 与字段前后值、受影响题数、`quick_check` / 外键 / 孤立父引用、回滚命令）。已补两份：`db_op_20261108_170620.json`（删 452 + 4 点改挂 + 18 题）、`db_op_20261108_172843.json`（新增 2 个板块 + 3 点改挂 + 3 题改挂 + 删 456）。**规则**：以后每次库变更（含手工 SQL）都要补一份，已写进 `db_ops.py` 头注释、本文件与 `04` |
| **D** 「台账统一结构」是过度声明 | **成立**：46 份台账标题集合没有两份相同，正文有 4 套骨架 | 降级为「**只统一 `\| 下一节计划 \|` 指针行**」：本文件第六轮小节标题与行名、`04` 第 2.1 节都改成「指针行统一」，并明写「不要据此认为台账骨架一致」。指针行本身仍是 46/46 命中、`ledger-sync --dry-run` 0 变更 |
| **E** 三份 g1 的顶部「当前进度」还是 11-07 的值，且「已用知识点」有两套 | **成立**：english/g1 顶部写 18 道 / 整单元节，当日 JSON 是 19 道 / `… / Ready Go`；chinese/g1、math/g1 的 11-08 4 个点只在批次段 | english/g1 顶部表整体换成 11-08 批次值（19 道 / `… / Ready Go` / 4 点 / 难度 3-4-9-2-1），并把两套清单合成一张「全部批次并集」表（8 条，带库内归属与「已并入」备注）；chinese/g1、math/g1 各补一行 11-08 历史行，并把当日 4 个点并入同一份「已用知识点」清单；三份都删掉末尾单独的 `## 已用知识点（本批次）` 块（`commit` 今后仍会按批次追加，属历史留痕，查重入口以顶部并集为准） |
| **F** 用户侧 9 条 live cron query 仍点名 4 节、缺 3.7 与复合名 | 用户侧事项 | 本目录只能给可粘贴句，见下节；其余 8 条不动 |

### 给用户侧 cron 的一句话补丁（只改英语那条）

在英语 query 的「三班职责」之后追加一句，其余 8 条不加：

```text
section 命名：英语必须写「Unit N 标题 / 板块」复合名（例：Unit 1 What is your family like? / Ready Go），板块只能取大纲本单元那串里的一个（Ready Go / Story / Practice / Communicate / Extend / Letters）；chapters[].name 仍写完整单元名，point 的 parent 与 section 完全一致。禁止只写纯板块名（Ready Go / Story 在 6 个单元里重复，无法定位单元），禁止自拟板块名；另需按 _daily-task-instruction.md 第零步~第六步执行，其中第一步 3.7「按大纲顺序取第一个未覆盖单元/节、不跳章不重复」必须遵守。
```

> 为什么只补英语：复合名是英语独有的约束（其他学科 `section` 就是大纲里的节名，扁平唯一）；3.7 是 9 条都该有，但用户侧 query 只点名了四节，这一句先解决英语的重复板块歧义，其余学科按用户意愿再动。

### 第七轮复核整改（2026-11-08 19:1x · 补题 + 规格升失败级 + 历史文件留副本）

| 项 | 判定 | 处理与实测 |
|---|---|---|
| **A** `600 Alphabet order` 只有 3 题，且「每点 ≥4」没有任何强制点 | **成立**：`591` 4 题、`600` 3 题；`verify_one` 当时把这条放在 `warnings`，`_validate_daily.py` 也不查，3 题的批次照样 `rc=0` | ① 给 11-07 JSON 补第 4 题（大小写配对选择题，难度 2，`Bb / Db / Pd / Qb` 选 A），并写库（`questions` 1086 → **1087**，新 id 1579，`600` 现有 4 题：1036–1038 + 1579）；改前备份 `ailearning-backup-20261108-190935.db`、留痕 `db_op_20261108_190935.json`。② `verify_one` 的「每点 ≥4」从 `warnings` 移入 **`errors`**，`all-verify` 判 fail、`ops import` 第 2 步直接中止；`tasks.json` 的 `verification_extra` 同步写明「fail 级，不接受事后凑数」。③ 实测当日不受影响：`all-verify --date 20261108` = `23 ok / 0 warn / 0 fail`；**历史批次被暴露**：`all-verify --date 20261107` = `通过 5 / 失败 21`（21 份都是真的每点 <4，另有 4 份还带大纲名越界），说明这条规格以前确实形同虚设。**该副作用已在第八轮收敛**：加规格生效日 + legacy 批次口径后，`all-verify --date 20261107` 变成 `试跑样本 26 / 失败 0`，细节见下节 |
| **B** 11-07 JSON 被就地改写，没有改前副本 | **成立** | `_archive/english_g1_first_20261107.pre-remap.json`：把 18:25 的两处改写做**逐字节逆操作**（含 CRLF），sha256 = `382ab2b5…` 与 manifest 里的**导入期 sha 完全一致**，即原件已成功还原；另存 `_archive/english_g1_first_20261107.pre-q4-add.json`（补第 4 题之前的精确字节副本）+ 同名 `.provenance.txt` 记录还原方式。**规则已写进 `04` §3.1**：改历史内容文件前先存 `_archive/<文件名>.pre-<变更名>.json`，与 `db_op_*.json` 同节，先存档再改 |
| **C** 用户侧 9 条 live cron query 仍未同步复合名 | 用户侧事项，不改本目录 | 可粘贴句在上一节「给用户侧 cron 的一句话补丁」，仍只改英语那条 |
| **D** 台账 4 套骨架仍在 | 已如实声明，不算问题 | 本次未动骨架；仅确认 `ledger-sync --dry-run` 仍 46 文件 0 变更 |
| **E** `591 Letters Aa to Dd` 与 `600 Alphabet order` 边界偏近 | **成立**：只靠备注不够，模型读并集表时容易混 | `ledger/english/g1.md` 的「已用知识点」表加**「适用边界（写新点前先比这条）」列**，9 条逐条写死：例如 `591` = **只做 Aa–Dd 四个字母的认读与读音**，`600` = **26 字母整体顺序 + 大小写配对**（Cc 大写形、Ee 前是 Dd、Gg 在 Ff 后、Bb 配对），并注明 Ee 及以后一律走 600 |

### 第八轮整改（2026-11-08 19:4x · 规格加批次门 + 历史批次口径 + 占位章节立项）

| 项 | 判定 | 处理与实测 |
|---|---|---|
| **A** 新硬规则把 11-07 整批染红（`通过 5 / 失败 21`） | **成立**：规格一旦从文字变成 fail，用新规则审判旧内容就会整片飘红 | `tasks.json` 新增 `policy.min_questions_per_point_since = "20261108"`：`verify_one` 里 ≥4 只对生效日之后的批次进 `errors`，更早批次降级为 `warnings` 并注明「批次早于规格生效日，按宽限处理」。`all-verify` 新增 `--spec-since`（临时覆盖生效日）与 `--include-legacy`（把 legacy 也计入未通过）。实测：`all-verify --date 20261107` = `通过 0 / 失败 0 / 缺文件 20 / 试跑样本 26`，结论=通过、EXIT=0；`--date 20261108` 仍 `23 ok / 0 warn / 0 fail`、EXIT=0 |
| **B** 11-07 的 8 册 math 挂在教材上没有的章节名下 | **成立，是真实教材错位**（不是规则误报）：g1 `10以内加减法` vs 大纲 `第四单元 10以内数加与减`；g2 `100以内加减法` vs `第一单元 100以内数加与减（二）`；g3 `一位数乘多位数`；g5 `小数除法`；g6 `圆`；g8 `勾股定理` vs `第一章 勾股定理` | **决策：标记 legacy、不重跑**。理由：① 这批内容已入库，重跑前必须先改库（把 148 道题的 `chapter_id` 迁到正式单元），而改库本身正是下面 C 的同一件事，不能拆开做；② 重跑要重新产出并覆盖已入库内容，风险大于收益，且 11-07 只是试跑样本。口径写进 `policy.legacy_batches_note` 与 `04`「历史批次口径（legacy）」。**注意**：这只是把问题「记账」，库里的错位章节仍然在（见 C），app 端仍能看到 |
| **C** 库里占位/旧样章与正式单元同级并列、order_index 撞号 | **成立，量级超出本自动化包 → 单独立项** | 新增只读巡检 `chapter_audit.py`（不改库），产出 `chapter_audit_20261108.json`：**146 册教材 / 657 章节 → 占位或旧样章 378 个、order_index 撞号 40 处**（math 83/15、chinese 118/9、english 90/10、politics 36/1、history 17/1、biology 14/2、geography 9/1、physics 7/1、chemistry 4/0）。抽查确认判定准确：math g1 上册 10 章里 `第一单元…第五单元` 全部 `in_outline=true`，而 `10以内加减法`/`开篇`/`比较与位置`/`认识图形`/`加与减（一）` 为占位；english g1 的 `Greetings 问候`/`Unit 1 Hello`/`Colours 颜色`/`Numbers 1-10` 为占位。本包**只出清单不动库**；清理方案（`chapters` 加 `is_placeholder` 标记，或按「大纲名 vs 库内名」对照摘除旧样章 + 迁移 11-07 那 8 册 math 的 chapter 与 148 道题）单独立项 |
| **D** 文档没有「11-07 的 21 份不达标怎么办」的口径 | **成立** | `04` 新增「历史批次口径（legacy）」小节；`00` 本节给出决策与理由。口径统一为：① 11-07 = 试跑样本，规格未达标，**不纳入回归基线**；② 20261108 起的新批次一律按硬约束（每点 ≥4 = fail 级）；③ 回头体检历史批次用 `all-verify --date 20261107`，看「试跑样本」区的遗留明细，要按旧口径判失败加 `--include-legacy` |
| 评审建议 4（把规格变成 fail 之前先在历史批次上跑一遍） | **采纳为流程规则** | 本轮即按此执行：先跑 → 看到 21 份变红 → 再决定配 grandfather（生效日 + legacy 名单）→ 最后改代码。以后凡「规格/校验从文字变成 fail」类改动，都必须先在历史批次上试跑并记录影响面 |

### 第九轮整改（2026-11-08 20:0x · 占位章节清理立项：阶段 1 已执行，阶段 2/3 已交付）

用户 2026-11-08 指示「**立项处理掉吧**」——把第八轮 C 项的占位章节问题从「只出清单」升级为**真正做掉**。立项书见 `05-占位章节清理立项.md`。

**先纠一个口径**：第八轮报的「占位 378 个」是错的（用大纲允许名集合判定，而大纲把 `认识更大的数`/`圆`/`勾股定理` 这类**简写名**也收进了允许名，漏判 + 假阳性并存）。改用**官方章节骨架**（`baseline/_skeleton_*`，由教材目录生成）作唯一基准后，真值是：**39 个旧样章 / 挂 297 题**（不是 378）。`chapter_audit.py` 已同步改成骨架口径。

| 项 | 处理 | 实测 |
|---|---|---|
| **阶段 1 · 库清理** | `alembic` 迁移 `a2b3c4d5e6f7`：`chapters` 加 `is_placeholder INTEGER NOT NULL DEFAULT 0` + `placeholder_note TEXT`；按判定表迁移 `questions.chapter_id`；迁移后空置的旧章删除；R-C 旧章 `is_placeholder=1` + `order_index` 沉底（9000+id）；教材真实章节 `order_index` 回写骨架序；`exams.chapter_ids` 引用同步改写 | `chapter_cleanup.py --confirm I_KNOW` EXIT=0：备份 `ailearning-backup-20261108-200922.db`；**chapters 657→642（删 15）**、**questions 1087→1087（零丢失）**、迁移 **167 题**、标记 **24 章**、序回写 **2 处**、考试引用修正 **2 条**；自检 `quick_check=ok` / 外键 0 / 悬空章引用 0 / **剩余撞号 0**；留痕 `db_op_20261108_200923.json` |
| **判定规则** | R-A 核心名唯一匹配（5 章 / 79 题）、R-B 显式映射（10 章 / 88 题，依据逐条写清）、R-C 保留待确认（24 章 / 130 题，**不硬归类**） | 判定表 `chapter_cleanup_plan_20261108.json`；R-B 逐题例外 4 条（chinese q614 整体认读音节→第四单元、biology q602/q604/q605 按知识点名分挂） |
| **阶段 2 · 归属确认清单** | 24 个 R-C 占位章逐条给：该册教材真实章节候选、每题知识点父链与题干摘要、原因 / 建议 / 风险 | `chapter_pending_map.py` → `chapter_pending_map_20261108.json`（24 章 / 130 题），只读不改库；结论回填判定表后重跑 `chapter_cleanup.py` 即可挂载 |
| **阶段 3 · app 过滤 + 导入保护** | app 端章节读取统一加 `is_placeholder == 0`（`public.py` 章节列表、`textbook_bundle.py` 离线包、`learn.py` ×2、`recommendation.py` ×3）；导入层加别名表 `backend/app/services/chapter_aliases.json`（旧章名→教材真实章节 / R-C 章名→建成占位章），旧 JSON 重导不再重建占位章 | 新增 `backend/tests/test_chapter_placeholder.py` 5 例 + 原 `test_content_import.py` 章节名改为教材真实章名（`加与减（一）` 已是旧样章名）→ **全量 365 例测试通过**；真库端到端：math g1 离线包 units = 6（库内 2 个占位章不再出现）、english g1 = 6、chinese g1 = 8、math g3 = 8 |
| **回归** | 清理不改变任何内容批次结论 | `all-verify --date 20261108` EXIT=0（23 ok / 0 warn / 0 fail）；`--date 20261107` EXIT=0（legacy 试跑样本 26）、`--include-legacy` EXIT=1（与清理前一致）；`ledger-sync --dry-run` 0 变更；`validate math g1/g9` EXIT=0；`chapter_audit.py` EXIT=0（未标记 0 / 撞号 0 / 序不一致 0） |

> **口径提醒**：清理只动 `questions.chapter_id` 与 `chapters` 的标记/序号，**不动知识点树、不改题、不删题**。R-C 的 24 章 / 130 题在库里**内容完整保留**，只是对用户不可见（占位章），等业务在阶段 2 清单里确认归属后再挂载。
>
> ⚠️ **这段口径已被下一节的阶段 4 取代**：用户 2026-11-08 指示「旧版数据删掉」，R-C 不再保留，已整章删除。

### 第九轮·阶段 4（2026-11-08 20:4x · 旧版数据整章删除 + 导入层堵回流）

用户指示：**「旧版数据删掉」**——不再等业务确认归属，教材目录上不存在的那批旧样章/旧专题**直接删除**。

| 项 | 处理 | 实测 |
|---|---|---|
| **删除范围（全部由库现状推导，不手写 id）** | ① `chapters.is_placeholder=1` 的 24 个占位章；② 挂在下面的 **130 道题**；③ 因此变空的 **61 个知识点**（37 个独占 point + 24 个独占 section，均为独占、无其它章共用）；④ `exams.chapter_ids` 里指向占位章的 id | `chapter_drop_legacy.py --confirm I_KNOW` EXIT=0：**chapters 642→618、knowledge_points 598→537、questions 1087→957**；自检 `quick_check=ok` / 外键 0 / 题目悬空章引用 0 / 题目悬空知识点引用 0 / 知识点悬空父引用 0 / **占位章剩 0** |
| **顺带修掉历史遗留** | `exams.chapter_ids` 里另有 9 个 id **在删除前就已失效**（前几轮删章节没同步考试引用）。规则：剔除全部失效 id；若剩余章数 < 该年级上册真实章数的一半，判定为「原本是整册范围、失效导致残缺」→ **按该年级上册全部真实章节整册重挂** | 3 份期末真题：exam1 `[311,4,5,6]`→`[307…312]`（g1 数学 6 章）、exam2 `[153,10,11,12]`→`[153…160]`（g1 语文 8 章）、exam3 `[42,43,44]`→`[321…328]`（g3 数学 8 章）；修后 **exam 悬空引用 0**（留痕 `db_op_20261108_204908.json`，备份 `ailearning-backup-20261108-204908.db`） |
| **堵回流（导入层）** | `chapter_aliases.json` 的 `placeholders` 段改语义为 **`discard`**：旧版数据章名 → **整章丢弃**（不建章、不挂题、不建知识点）；旧样章名 → 仍重定向到教材真实章节 | 导入报告新增 `chapters_discarded` / `questions_discarded` / `knowledge_discarded`；被丢弃板块的前置知识引用改为**跳过而非报错**（`politics.json` 的「学习伴成长→中学时代」不再炸） |
| **重导不会复活（实测）** | 旧 `templates/*.json` 重导到临时库副本 | `politics` / `geography` 各**丢弃 1 章 + 5 题 + 4 知识点**；`math`/`biology`/`chinese`/`english` 走 alias 重定向或已存在；**旧章残留：无** |
| **基线同步** | kp 基线 598 → **537 个名字 / 0 歧义**（重写到 `baseline/_knowledge-points-baseline_latest.json`，daily 任务实际读取处）；章节基线重建（不再列占位章） | `build_kp_baseline --output-dir baseline` + `build_chapters_baseline` 均成功 |
| **回归** | 删除不改变任何内容批次结论 | `chapter_audit.py` EXIT=0（146 册 / **618 章** / 占位 0 / **未标记 0** / 撞号 0 / 官方章序与骨架不一致 0）；`all-verify --date 20261108` EXIT=0；`--date 20261107` EXIT=0（legacy 26 份）、`--include-legacy` EXIT=1；`validate --subject math --grade 1` EXIT=0；`ledger-sync --dry-run` 0 变更；`pytest` **365 例全通过**；真库离线包 units：math g1 = 6、chinese g1 = 8、math g3 = 8、english g1 = 6（全为教材真实章节） |
| **副作用（如实披露）** | 删除的是旧版内容，**这些年级/学科的题量随之归零** | **math g3 上册现为 0 题**（原 18 题挂在旧章「一位数乘多位数」）；g3 的 exam 已整册重挂，待教研补题后可用；chinese g1 上册 48 题、math g1 上册 48 题不变 |

> **不变的部分**：教材真实章节（618 个）、知识点树主体、957 道题的内容全部原样保留；删除的只是「教材目录上不存在」的那 24 章 + 其 130 题 + 61 个随之变空的知识点。

### 第十轮整改（2026-11-08 21:2x · 第九轮评审 4 条建议）

第九轮评审认定主线已完成，但指出**两件被清理掩盖的事** + 一个文档口径错误。逐条落实：

| 评审意见 | 落实 | 实测 |
|---|---|---|
| **建议 1：出覆盖缺口清单，固化进 04**（「干净」与「齐不齐」两件事并列） | 新增只读巡检 `coverage_gap.py` + `coverage_gap_20261108.json`；口径写进 `04` §3.5；`tasks.json` 的 `policy.coverage_gap_note` 登记 | 73 册上册（**46 册有骨架**，其余 27 册空册不计入分母）/ 教材真实章 **307** / 有题 **53** / **0 题 254** / 题目 957 / **整册空 2 册**；分科：math 71、chinese 56、english 48、politics 27、history 15、physics 13、biology 10、geography 8、chemistry 6 个 0 题章 |
| **建议 4：math g3/g5 进「待重跑」队列，别在覆盖台账显示成已完成** | `tasks.json` → `policy.rerun_queue` 登记 2 册（附原因与处置口径）；`coverage_gap.py` 每次运行与库实况**对账** | 对账输出：「待重跑登记对账：math g3 first → 一致（0 题）」「math g5 first → 一致（0 题）」；登记一旦与实况脱节会打印「**已不成立**（该册已有题，登记可撤）」 |
| **建议 2a：给 8 份 11-07 math JSON 加 legacy 标记** | 顶层加 `"_legacy": true` + `"_legacy_note"`；改前**逐字节**副本存 `_archive/math_g*_first_20261107.pre-legacy-mark.json` + `math_11-07_legacy-mark.provenance.txt`；**同步 `_import-manifest.json` 里 8 条 sha256**（不否则校验器会把「sha 与导入期不一致」当新版本、从严报重名 → 11-07 批次假红） | 8 份 sha 全部更新、8 份副本 + provenance 落盘；`all-verify --date 20261107` 仍 **EXIT=0**（试跑样本 26，未假红）；`validate --subject math --grade 1 --date 20261107` 由 **EXIT=1 → EXIT=0**（章节名不在大纲内降级为 legacy 提醒） |
| **建议 2b：discard 走「报告单独列丢弃项」而不是静默** | 导入报告新增 `discarded_detail` + `legacy_file`；`scripts/import_content.py` 对 legacy 文件打一行提示、对丢弃项**单独成行** | dry-run 实测：`已丢弃（旧版数据，不入库）：math g3 · 18 题 · 章 1 · 知识点 6 · [一位数乘多位数]`、`math g5 · 18 题 · 章 1 · 知识点 6 · [小数除法]`；g1/g2/g4/g6/g7/g8 走 aliases 重定向并带 legacy 提示 |
| **建议 3：05 第 115 行 `placeholders` → `discard`** | `05` §5 阶段 4 第 3 条与 `00`/`04` 统一改为 **`discard` 段**，并注明「该文件里没有 `placeholders` 键」 | 文档已改 |
| **建议 E：A10/A12 标注验证方** | `05` 验收表加「验证方」列：A1–A9 标「运维自测 + 第九轮评审独立复跑」，**A10/A12 标「运维侧声明（第九轮评审未独立复跑）」**；并附任何人可自行核对的复跑命令 | 文档已改 |

> **顺带查清的两个数字口径差异**（避免下轮再争议）：`math g3` 旧章「一位数乘多位数」**库内 22 题**、**JSON 内只有 18 题**（差 4 题来自其它批次，不在该 JSON 里）；`math g5`「小数除法」库内与 JSON 均 18 题。删除按**库内**口径执行（合计 130 题）。

### 第十一轮整改（2026-11-08 21:5x–22:0x · manifest 语义地基 + 只读巡检 + 空态）

第十一轮评审认定前一轮落地到位，但指出**唯一有分量的隐患在 `_import-manifest.json`**：为让 legacy 文件不假红而就地刷 sha，等于把「已入库」的判据从「内容与导入时一致」降级成「文件被登记过」。逐条落实：

| 评审意见 | 落实 | 实测 |
|---|---|---|
| **A（P1）manifest 拆 `imported_sha256` / `current_file_sha256`** | ① manifest 每条拆三列：`imported_sha256`（**导入当刻，永不改写**）/ `current_file_sha256`（盘上现值）/ `imported_content_sha256`（导入当刻**剔除元数据键**后的内容哈希），旧 `sha256` 键删除；② 校验器 `_manifest_import_state` 判**三态**：`unchanged`（字节一致）/ `meta_only`（字节变、内容同 → 仍算已入库）/ `changed`（内容也变 → **从严检查**）；③ 迁移脚本 `migrate_manifest_3col.py` 落三列（8 份 legacy 的 `imported_sha256` 取**打标记前副本**的 sha——`_archive/*.pre-legacy-mark.json` 就是导入当刻字节）；④ `import_content.py` 写入按三列、`db_ops.py` 的待导入判定同步 | 迁移 49 条：**41 unchanged + 8 legacy_meta_only + 0 missing**（留痕 `_archive/_import-manifest.pre-3col.json` + `.provenance.txt`）；三态实测：未变更 → `[已入库]`、11-07 legacy → `[已入库·仅元数据变更]`、临时改 1 个题干 → `[文件已变更·未重导]`（还原后回到 `[已入库]`）；`all-verify --date 20261107` 仍 **EXIT=0** |
| **B（P1）两个只读巡检改 `mode=ro`** | `chapter_audit.py` / `coverage_gap.py` / `chapter_pending_map.py` 统一 `sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)`；04 新增 §3.6「只读巡检验收标准」 | 跑前跑后 `ailearning_dev.db` mtime **均为 `21:51:29.478`（不变）**；`chapters 618 / knowledge_points 537 / questions 957` 不变；`chapter_audit.py` EXIT=0、`coverage_gap.py` EXIT=0 |
| **C 覆盖率分子分母写清** | 04 §3.5 补「分母口径」框：分母 = **上册且有官方骨架的 73 册 / 307 章**（不是全库 `146 册 / 618 章`）；点名 **27 册无骨架 = 高中 9 学科 × g10–g12**（人教版·外研版·部编版），属「另一条任务线」——**既判不了覆盖、也巡检不了占位，是当前口径盲区** | 27 册清单已落进 `coverage_gap_20261108.json`（`status=no_skeleton`），04 §3.5 逐条列出 |
| **D-1 app 端空态文案** | 练习页 `Center(Text('暂无题目'))` → `_EmptyPracticeState`（沙漏图标 +「本节内容准备中」+「该节暂无题目，教研内容正在补充中。可先返回教材目录浏览其它已更新的章节。」）；单元页「该单元暂无知识点内容，敬请期待。」→「本单元内容准备中，教研内容正在补充中。」；节级「本节暂无知识点」→「本节内容准备中」 | `flutter analyze` → **No issues found!**（2.3s） |
| **D-2 legacy 标记只能人工运维** | 04 新增 §3.7「历史内容文件的人工禁令」：改历史内容文件的脚本**只能人工运维执行**，教研会话不得调用/自行改历史 JSON；执行前留逐字节副本 + provenance；执行后只同步 manifest 的**当前值**两列，`imported_sha256` 不改 | 文档已出 |
| **防漂移测试** | 三处 `content_sha256` 实现（`content_import.py` 权威 / `_validate_daily.py` 校验 / export 包 3 个脚本）必须一致，否则「仅元数据变更」判定会失效 | 新增 `backend/tests/test_manifest_content_hash.py` 5 例（一致性 + 元数据不影响哈希 + 内容变更必变 + 三态端到端）；全量 **370 例通过** |

### 第十二轮整改（2026-11-08 22:2x · 第十一轮评审 4 条）

第十一轮评审确认 manifest 地基已治好（49 条全量重算 = 41 字节一致 + 8 仅元数据 + 0 变更 + 0 缺失；`_manifest_import_state` 五个分支单测全中；两个巡检跑完库 mtime 不动；`pytest 370 passed`），但指出**问题已经不在数据库，而在交付件**。逐条落实：

| 评审意见 | 落实 | 实测 |
|---|---|---|
| **A（P1）交付包里放的是「不要用我」的冻结快照** | ① `exports\automation_20261108\_validate_daily.py` 用**内容根现行版逐字节覆盖**（`39027 B / 832 行`）；② 那份 719 行冻结快照移入 `_archive\_validate_daily.frozen-20261108-2214.py` + provenance（记 size/行数/双份 sha256/为什么挪）；③ `00-导入说明.md` 第 12 行改「本包内这份 = 内容根现行版的逐字节副本」，并新增「校验器版本」一节（三态 + `_legacy` 支持、必须与 `baseline\` 同级才完整生效）；④ `00` 第 392 行「两份 SHA256 亦相同」原本不成立，现**重新成立**并写明旧快照去向 | 包内与内容根 `sha256` 均为 `c9d80e7cc6404c84…`；冻结快照 `20160bf4942b89ef…` 已归档；留痕 `_archive\_validate_daily.frozen.provenance.txt` |
| **B（P1）7 份 `db_op` 三套骨架，删得最多的两次缺 `changes`/`rollback`** | `chapter_cleanup.py`（阶段 1）与 `chapter_drop_legacy.py`（阶段 4）的报告在保留原有 `deleted_chapters` / `marked_chapters` / `migrated` / `deleted` / `exams_fixed` 的同时，**新增统一字段** `changes`（逐行改动记录，用各脚本真实字段名）与 `rollback`（`{backup, command}`）；04 新增 §3.1.1「`db_op_*.json` 统一骨架与历史字段映射」 | 历史 7 份 JSON **一字未改**（留痕不动）；两脚本 `py_compile` 通过；字段映射表覆盖 `migrated`/`deleted_chapters`/`deleted` → `changes`、`_meta.restore_hint` → `rollback` |
| **C（P2）一次无谓 touch** | `math_g9_first_20261108.json` mtime 22:04 但 sha 与导入当刻相同（内容一字未改地重写了一遍）；写盘防线改为「**字节一致就不落盘**」：`migrate_manifest_3col.py`、`mark_legacy_json.py` 都加 `write_if_changed()`；04 新增 §3.1.2 立规 | `migrate_manifest_3col.py` 复跑打印「[幂等] … 49 条：unchanged 41 / legacy_meta_only 8，本次不落盘」且 `_import-manifest.json` **mtime 仍是 22:03:22**（sha 未变）；`mark_legacy_json.py` 零变更复跑不再重写留痕文件 |
| **D（P2）05 的「18 题」与 `tasks.json` 的「22 题」口径没标** | `05` 第 133 行补注：「18 题 = 该 JSON 内题数；库内该章 22 题（差 4 题来自其它批次），删除按**库内**口径执行」 | 文档已改（`00` 第十轮已有一节同口径说明，两处对齐） |

> **顺带发现并修掉的一个真 bug（整改过程中自己踩到）**：复跑 `mark_legacy_json.py` 时它会**无条件重写** `_archive/math_11-07_legacy-mark.provenance.txt`；这次 8 份都已标记（`touched` 为空），于是「逐份明细」被写成空段落、原记录被覆盖。已改为「零变更不写 manifest、也不重写留痕」，并按 21:21:48 原文逐行还原该文件（末尾留「补记」说明经过）。`pytest` 5 例 manifest 哈希一致性测试通过。



## 前置条件（已在本机核验）

- `backend\.venv\Scripts\python.exe` 存在（Python 3.10.11），`py_compile` 通过。
- 内容根的 `_daily-task-instruction.md` 与导出副本 **SHA256 相同**；`_validate_daily.py` **亦相同**（2026-11-08 22:0x 整改：`exports\automation_20261108\_validate_daily.py` 已用现行版 `39027 B / 832 行`、sha256 `c9d80e7cc6404c84…` 覆盖，那份「单列 sha、不认 `_legacy`」的 719 行冻结快照移到 `_archive\_validate_daily.frozen-20261108-2214.py` 留痕）→ 改写版直接引用工作副本，不需要搬目录。
- **自检必须用内容根的 `_validate_daily.py`**：脚本按 `__file__` 所在目录找 `baseline\` 和 `_import-manifest.json`；导出包里那份副本的目录没有 `baseline\`，在原地跑大纲范围校验会失效（换机后把副本拷进目标机内容根即可，那时它=内容根那份）。

## 手动执行（一次完整闭环）

```powershell
$py  = 'D:\ai\prj\trae\HuaWei\AiLearning\backend\.venv\Scripts\python.exe'
$run = 'D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\_run_daily.py'

# 1) 看参数 / 出计划（只读）
& $py $run list
& $py $run plan --subject math --shift 02 --date 20261108 --json

# 2) 加锁 → 逐年级 context → write_to_file 生成 JSON → validate → commit → finish
& $py $run lock   --subject math --action acquire --date 20261108
& $py $run context  --subject math --grade 1 --date 20261108
& $py $run validate --subject math --grade 1 --date 20261108
& $py $run commit   --subject math --grade 1 --date 20261108 --minutes 5 --dry-run   # 先看要写什么
& $py $run finish   --subject math --date 20261108 --done 1 --minutes 5
```

更省事的做法：把 `01-主提示词.md` 的代码块粘到全新会话，只替换 `{SUBJECT}` / `{SHIFT}` / `{BATCH_DATE}`；或运行 `python _run_daily.py prompt --subject math --shift 02` 拿到参数已展开的完整长提示词。9 条任务各自的短 query 在 `02` 文件里。

## 定时执行（可选，本次未注册）

`03-自动化注册清单.json` 是 27 条 `automation_update`（`mode=suggested create`）的**审阅稿载荷，当前禁止注册**（顶层 `registration.allowed=false`）：

- 启用形态已按用户拍板定为 **B**：9 学科 × 3 班次 = 27 条，`BYHOUR` 为 `2 / 12 / 21`。02/12 两班 `BYMINUTE` 沿用各学科原值 0/5/…/40；原 22 点班前移到 21 点档，`BYMINUTE=30..38` 按学科顺序每分钟一条（21:30–21:38）。理由：21:30–21:59 只剩 30 分钟，放不下 9×5 分钟错峰；各学科锁文件独立，1 分钟错峰不触发同科并行锁；距「最迟 23:30 停手」≥1h52m。
- `cwds` 固定 `D:/ai/prj/trae/HuaWei/AiLearning`；`status` 全部 `PAUSED`，与原文「当前状态：已停止」一致。
- **启用前置条件（尚未完成）**：先停用原文 9 条 cron（两套调度不得同时 ACTIVE），逐条复核 27 条 RRULE / cwds / prompt，再把 `status` 改为 `ACTIVE`。在此之前禁止把本文件喂给 `automation_update`；02/12 两班仍与原文 cron 同分钟。
- 每条 prompt 自带学科/年级/版本/班次与绝对路径，指向 `01-主提示词.md` 与 `tasks.json`，符合「定时任务触发时是全新会话，参数必须写进任务正文」的前提。
- **本次没有实际创建任何自动化**，`automation_update` 本轮及此前从未被调用。

## 验证记录（2026-11-08；教研动作只读，入库/回退为人工运维实测）

| 检查 | 结果 |
|---|---|
| `python -m py_compile _run_daily.py` | `COMPILE=0` |
| `list` | 9 条任务参数与原文一致（学科/年级/版本/cron 全对齐） |
| `plan --subject math --shift 12 --date 20261108 --now 12:00` | 8 个年级缺文件 → 补漏班截到 `[1,2,3]`，其余顺延，退出码 0 |
| `plan --subject biology --shift 22 --date 20261108 --now 23:45 --no-check` | 触发「已过 23:30 停手」，待办为空、只记无待办日志，退出码 0 |
| `validate --subject math --grade 9 --date 20261108` | 真实文件自检通过 `EXIT=0`（4 知识点 / 18 题） |
| `commit --subject math --grade 9 --date 20261108 --dry-run` | 正确生成台账段（题型/难度/来源/统计）与运行日志行，**未写任何文件** |
| `context --subject math --grade 4 --date 20261108` | 只输出四年级大纲段 + 查重清单 + 台账尾部，退出码 0 |
| `prompt` / `payload` / `payloads` | 退出码 0；`03` 文件 27 条载荷、JSON 可解析、UTF-8 无 BOM |
| `plan --json` 经 `subprocess` 捕获后 `json.loads` | 合法 JSON：`todos=[1..8]`、`idle=false`、`lock.state=none`，每年级带 `next_section` |
| `progress` 抽查 9 个学科年级 | 均算出具体下一节（语文 g1 `4 日月山川`、化学 g9 `课题2 …`、数学 g9 `3.矩形的性质与判定` 等），退出码 0 |
| `commit --dry-run` 复查台账段 | 「下一节计划」已是具体节名 + 单元 + order_index，不再是占位文本；**未写任何文件** |
| 一键入口 `run.ps1 -Subject math -Shift 02 -Date 20261108` | 退出码 0；输出含只读计划与完整提示词，`BATCH_DATE = 20261108` 已写死、无 `<BATCH_DATE>` 占位符 |
| 一键入口 `-Action check` / `-Action commit -DryRun` | 均退出码 0；`commit -DryRun` 只预览台账/日志，不写文件 |
| `run.cmd` 包装器 / 非法 `-Subject` | 包装器透传参数退出码 0；非法学科退出码 1 并报 `Unknown subject` |
| 一键执行后的副作用检查 | 锁文件 0 个；`daily/ledger/logs` 在 08:00 后被改动文件 0 个；未生成 `last-prompt.md` |
| `all-plan --date 20261108` 连跑两次 | 两次 JSON 输出完全一致（`IDEMPOTENT=True`）：早期 45 年级口径下试跑前 19 已完成 / 26 缺文件、试跑 3 个年级后 22 已完成 / 23 缺文件、0 待修、6 学科无待办；**当前 46 年级口径为 done 23 / missing 23 / repair 0 / idle 6** |
| `all-verify --date 20261108` / `--strict` | 新增两条分布验收后曾为 5 `ok` / 17 `warn`；补题、调难度并并入 `math/g9` 后为 23 `ok` / 0 `warn`；复评后把 `_validate_daily.py` 的 6 条 `[提醒]` 并入 `warnings`，**当前为 21 `ok` / 2 `warn` / 0 `fail` / 23 缺文件 / 20 条记录提示**；非严格退出码 0，严格退出码 1（23 个年级待产出 + 物理 g8 / 地理 g8 的校验器提醒） |
| `math/g9` 并入后只读复核（最终口径） | `all-plan --json`：`subjects 9, grades 46, done 23, repair 0, missing 23, todo_grades 23, idle_subjects 6`；`all-verify --json`：`grades 46, ok 21, warn 2, fail 0, missing 23, notes 20`；`math/g9 status=done valid=True next_section=3.矩形的性质与判定` |
| 评审整改后回归（10:03） | `_run_daily.py` 不含 `sqlite3` / `import_content` / `db_backup`；`import` / `restore` 子命令退出码 2（invalid choice）；`db_ops.py` 缺 `--confirm I_KNOW` 退出码 2；`-Action import` 幂等重跑 EXIT=0、0 份待导入、全表增量 0；`--now 23:45` 不带 `--shift` 推断为 22 班且给提醒；老格式台账 `commit --dry-run` 显示 `ledger_skip=True`；四个只读动作与 27 条载荷禁令均通过 |
| 收尾复核（17:18，最终口径，取代上面两行「当前为」的旧数字） | `all-plan --json`：`subjects 9, grades 46, done 23, repair 0, missing 23, todo_grades 23, idle_subjects 6`；`all-verify`（非严格）：`46 年级，通过 23 / 提醒 0 / 失败 0 / 缺文件 23`，学科明细 math 2、chinese 1、english 1、politics 9、physics 2、chemistry 1、biology 2、history 3、geography 2，另有 20 条「台账/日志未覆盖历史文件」记录提示（非内容问题），结论=通过、退出码 0 |
| 收尾复核：调度与禁令一致性 | `03` 27 条载荷 `status` 全 `PAUSED`、`mode` 全 `suggested create`、顶层 `registration.allowed=false`；`BYHOUR` 分布 `{2:9, 12:9, 21:9}`；27 条 prompt 均含「禁止调用 db_ops.py」「不导入、不连库」「`_run_daily.py` 已无 import/restore」三条禁令（0 违反）；`tasks.json`：`policy.rrule_minute_offset=0`、`policy.min_questions_per_point=4`、`policy.shift_hours={02:2,12:12,22:21}`、`compulsory_scope.math=[1,9]`、`tasks[].grades` 合计 46 |
| 收尾复核：班次口径与入口 | `--now 23:45` 推断 22 班并给「已过 23:30 停手」提醒、`--now 03:10` 推断 02 班，均带「与真实时刻不一致」提醒；`run.ps1 -Subject math -Shift 22 -Date 20261108` EXIT=0、班次标签显示「补漏班·前移至21:30」；`01`/`02` 已补写「班次口径」（`02/12/22` 是逻辑标签、`22` 班载荷前移 21:30–21:38、两份文件是会话照办的现行表而非历史记录） |
| 实跑一次全科流程（math/chinese/english g1） | 3 份 JSON 各 4 知识点 / 18 题 / 5 种题型 / 0 重复题干，`validate` 均 EXIT=0（0 错误 0 提醒）；`commit` 台账写入具体下一节，`finish` 释放锁后锁文件 0 残留；进度指针分别推进到 `第一单元 生活中的数` / `语文园地一` / `Story` |
| 第八轮复核（19:4x） | 批次门生效：`all-verify --date 20261108` = `23 ok / 0 warn / 0 fail / 23 缺`、EXIT=0；`--date 20261107` = `通过 0 / 失败 0 / 缺文件 20 / 试跑样本 26`、EXIT=0（`--include-legacy` → EXIT=1）；`--spec-since 20260101` 覆盖生效日；`chapter_audit.py` 巡检 → 146 册 / 657 章节 / 占位或旧样章 378 / `order_index` 撞号 40；`ledger-sync --dry-run` 0 变更；`validate --subject english --grade 1 --date 20261108` EXIT=0；lint 0 |
| `all-prompt --date 20261108` | 退出码 0；BATCH_DATE 写死、无占位符、包含 `all-verify --strict` 核实步骤 |
| 占位章节清理 · 阶段 1 实测（20:0x） | `chapter_cleanup.py --dry-run` 预检通过（15 迁移 / 24 保留 / 2 序回写）；`--confirm I_KNOW` EXIT=0：**chapters 657→642、questions 1087→1087（零丢失）**、迁移 167 题、删 15 章、标记 24 章、考试引用修正 2 条；`quick_check=ok` / 外键 0 / 悬空 0 / 剩余撞号 0；留痕 `db_op_20261108_200923.json`（含备份路径与回滚命令） |
| 占位章节清理 · 阶段 2/3 实测（20:1x） | `chapter_pending_map.py` → 24 章 / 130 题清单（只读）；`chapter_audit.py` EXIT=0（146 册 / 642 章节 / 已标记占位 24 / **未标记 0** / 撞号 0 / 官方章序与骨架不一致 0）；新增 `tests/test_chapter_placeholder.py` 5 例全绿；`pytest -q` 全量 **365 例通过**（Windows 下需 `PYTHONUTF8=1`，否则 `alembic.ini` 被 GBK 读会炸——**环境问题，非本次改动**）；真库端到端：math g1 / english g1 / chinese g1 / math g3 的离线包 units 分别 6 / 6 / 8 / 8，**占位章不再出现在教材目录视图** |
| `run_all.ps1` 默认 / `-Action verify` / `-Action verify -Strict` | 退出码 0 / 0 / 1，输出分别含计划+提示词、`ALL-VERIFY PASSED`、`NOT PASSED`；`run_all.cmd` 包装器退出码 0 |
| **阶段 4：旧版数据整章删除（20:4x）** | `chapter_drop_legacy.py --dry-run` 预检：24 章 / 130 题 / 61 独占知识点 / 3 条考试引用；`--confirm I_KNOW` EXIT=0 → **chapters 642→618、knowledge_points 598→537、questions 1087→957**；自检 `quick_check=ok` / 外键 0 / 题目悬空章 0 / 题目悬空知识点 0 / 知识点悬空父引用 0 / 占位章 0；第二次执行修 exam 引用 → **exam 悬空引用 0**、EXIT=0；留痕 `db_op_20261108_204703.json`（备份 `…-204703.db`）与 `db_op_20261108_204908.json`（备份 `…-204908.db`） |
| 阶段 4 回归与堵回流 | `chapter_audit.py` EXIT=0（146 册 / **618 章** / 占位 0 / 未标记 0 / 撞号 0 / 序不一致 0）；`all-verify --date 20261108` EXIT=0、`--date 20261107` EXIT=0（`--include-legacy` → 1）；`validate --subject math --grade 1 --date 20261108` EXIT=0；`ledger-sync --dry-run` 0 变更；`pytest` **365 例通过**；旧 `templates/*.json` 重导到临时库 → politics/geography 各丢弃 1 章 + 5 题 + 4 知识点，**旧章残留：无**；kp 基线重建 537 名字 / 0 歧义；真库离线包 units：math g1 = 6 / chinese g1 = 8 / math g3 = 8 / english g1 = 6（全为教材真实章节） |
| 换日推进模拟（只读，不写文件） | 化学 g9、语文 g1、数学 g4 的 `next_section` 均前进到下一节 |
| 第十轮：覆盖缺口巡检（21:2x） | `coverage_gap.py --out coverage_gap_20261108.json` EXIT=0：**73 册上册（46 册有骨架）/ 307 官方章 / 有题 53 / 0 题 254 / 题目 957 / 整册空 2 册**（math g3 8 章、math g5 12 章）；待重跑队列对账「一致（0 题）」×2 |
| 第十轮：8 份 11-07 math JSON 打 legacy 标记（21:2x） | `mark_legacy_json.py` → 8 份加 `_legacy`/`_legacy_note` + 8 份改前副本 + `math_11-07_legacy-mark.provenance.txt` + manifest 8 条 sha256 同步；`all-verify --date 20261107` 仍 EXIT=0（未假红）；`validate --subject math --grade 1 --date 20261107` 由 EXIT=1 → **EXIT=0**（legacy 降级为提醒） |
| 第十轮：discard 单独成行（21:2x） | `import_content --path daily/math --pattern "*_20261107.json" --dry-run` → 「已丢弃（旧版数据，不入库）：math g3 · 18 题 · 章 1 · 知识点 6 · [一位数乘多位数]」、g5 同款；g1/g2/g4/g6/g7/g8 走 aliases 重定向并带 legacy 提示行 |
| 第十一轮：manifest 三列迁移 + 三态判定（22:0x） | `migrate_manifest_3col.py` → 49 条（41 unchanged + 8 legacy_meta_only + 0 missing），留痕 `_archive/_import-manifest.pre-3col.json` + `.provenance.txt`；三态实测：未变更 → `[已入库]`、11-07 legacy → `[已入库·仅元数据变更]`、临时改 1 个题干 → `[文件已变更·未重导]`（还原后回到 `[已入库]`）；`all-verify --date 20261107` 仍 EXIT=0 |
| 第十一轮：只读巡检 mode=ro（22:0x） | 跑前跑后 `backend/ailearning_dev.db` mtime **均为 21:51:29.478（不变）**；`chapter_audit.py` EXIT=0（占位 0 / 未标记 0 / 撞号 0 / 序不一致 0）、`coverage_gap.py` EXIT=0（254 个 0 题章 + 2 册整册空 + 对账一致）；库计数 618 / 537 / 957 不变 |
| 第十一轮：app 空态 + 防漂移测试（22:0x） | 练习页空态改为 `_EmptyPracticeState`（图标 +「本节内容准备中」+引导），单元页/节级空态同步；`flutter analyze` → **No issues found!**；新增 `tests/test_manifest_content_hash.py` 5 例，全量 `pytest` **370 例通过** |
| 全学科验证后的副作用 | 锁文件 0 个；`daily/ledger/logs` 在 08:00 后被改动文件 0 个 |
| `import --date 20261108 --dry-run` | 退出码 0；先生成备份 `ailearning-backup-20261108-092350.db`，试跑 23 份文件后回滚，数据库计数不变 |
| 一键 `-Action import` 正式入库（首轮 09:24） | 退出码 0；备份 `...-092404.db`（`quick_check=ok`）；`dry-run` 与正式导入均 EXIT=0；知识点 581→596、题目 1004→1058；三份新文件各 18/18 题干在库中查到；manifest 三条 `status=ok` |
| 重复 `-Action import` | 0 份待导入、全表增量 0（幂等） |
| 数据修复 + `-Action import -Overwrite`（10:22） | 18 份文件补 28 道原创题、29 处难度调档；备份 `...-102220.db`；`pending 18`、`dry_run_rc=0 / import_rc=0`、`questions 1058→1086`（+28）、18 份文件逐题 `stems_in_db` 全命中；报告 `import_report_20261108_102222.json` 的 `all_new_stems_in_db=true`；当前库 `596 知识点 / 1086 题`、`PRAGMA quick_check=ok` |
| `ledger-sync --date 20261108 --confirm I_KNOW` | 22 份台账 / 55 行就地重算；复核题量 `MISMATCH=0`、占位下一节 `PLACEHOLDER_LEFT=0`；无 `--confirm` 与错误 confirm 均退出码 2；`--dry-run --json` 复跑 `changed_files=0 / changed_lines=0`（幂等） |
| 一键 `-Action restore` | 已验证安全分支：备份路径不存在、未加 `--force` 均退出码 2 且不写库；**未实际回退生产库**（当前库数据正常），回退命令与备份路径已写入报告与说明 |
| IDE 诊断 | `00` / `04` 文档与 `run.ps1` / `run_all.ps1` / `run_all.cmd` 0 错误 0 警告；三个 `.py` 在 basedpyright 严格模式下有**预存**的类型标注告警（`dict` 未写类型参数、动态属性推断等），本轮未改动类型逻辑，`ast.parse` / `py_compile` 与实际执行全部通过 |

> 验证时踩过一次 PowerShell 5 管道编码：`plan --json | python -c "json.load(sys.stdin)"` 会因管道被加上 BOM 报 `Expecting value: line 1 column 1`；改用 `subprocess.run(..., capture_output=True, text=True, encoding='utf-8')` 或直接读会话里的工具输出文本即可，脚本本身输出的是合法 JSON。

## 口径与已知差异（不是"改规则"，是把原文冲突点写清楚）

1. **`--kp-baseline` 默认不传**：原导出 9 条 query 明确写「按用户『今天不用管库里的内容』口径，不传 `--kp-baseline`，重名交给入库时自动后缀」；而通用指令文件的第五步仍带它。改写版按**较新的 9 条 query 口径**执行，需要更严时给驱动加 `--with-kp-baseline`。
2. **`math` 年级已扩到 1-9**：原导出任务只到 8 年级，工作区另有 `math\g9\math_g9_first_20261108.json` 与 `_outline_math_g9_first_latest.md`。按评审意见并经用户确认，`tasks.json` 的 `math.grades` 改为 `[1..9]`（全景 45→46 年级），`02` 的任务名/表格与 `03` 的 27 条载荷同步重生成；`outline_by_grade` 原本已为 g9 配好大纲，原文一律未改。
3. **大纲自动发现的既有行为**：`_validate_daily.py` 会扫描脚本同目录 `baseline\` 下所有 `_outline_*_latest.md`，后读到的同名 `subject:semester` 会覆盖先读到的；驱动仍显式传 `--outline`，但这属于原脚本行为，改写版没有改它。
4. **日期时区**：用系统本地时间（本机即 Asia/Shanghai），跨零点一律用 `--date` 固定 BATCH_DATE；22:00 班 `--now >= 23:30` 自动收手。
5. **边界不变**：教研生成流程只产出 JSON + 追加台账/日志；不执行 `scripts/import_content`、不连数据库、不跑 alembic、不修改任何已有内容文件、不读写其他学科文件。入库/回退是**独立且必须显式触发**的人工运维环节（见上面「一键入库」与 `db_ops.py`，写库需 `--confirm I_KNOW`）；生成提示词里不会自动入库。
