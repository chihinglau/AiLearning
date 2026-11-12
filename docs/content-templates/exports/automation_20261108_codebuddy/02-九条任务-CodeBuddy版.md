# 九条任务 · CodeBuddy 版 query（原文 9 段 query 的逐条改写）

- 对应原文：`..\automation_20261108\01-九条任务全文可复制.md` 的 9 个代码块。
- 每段的「执行体」统一指向本目录 `01-主提示词.md`（唯一指令源，改规则只改那一处）；参数以 `tasks.json` 为准，确定性动作交给 `_run_daily.py`。
- 复制任意一段到全新会话即可执行；也可运行 `python _run_daily.py prompt --subject <学科> --shift <班次>` 生成把执行体展开后的完整长提示词。
- 共享常量（每段首行已自带）：
  `$PY='D:\ai\prj\trae\HuaWei\AiLearning\backend\.venv\Scripts\python.exe'`
  `$RUN='D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\_run_daily.py'`
  `$CB='D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\01-主提示词.md'`

| # | 原文标题 | subject / grades / version | 原 cron | CodeBuddy 班次（`--shift` 标签 / 原文 cron 时刻） |
|---|---|---|---|---|
| 1 | 数学1-9上每日教研 | math / 1-9 / 北师大版 | `0 2,12,22 * * *` | 02:00、12:00、22:00 |
| 2 | 语文1-9上每日教研 | chinese / 1-9 / 人教版 | `5 2,12,22 * * *` | 02:05、12:05、22:05 |
| 3 | 英语1-9上每日教研 | english / 1-9 / 牛津深圳版 | `10 2,12,22 * * *` | 02:10、12:10、22:10 |
| 4 | 道法1-9上每日教研 | politics / 1-9 / 部编版 | `15 2,12,22 * * *` | 02:15、12:15、22:15 |
| 5 | 物理8-9上每日教研 | physics / 8-9 / 人教版 | `20 2,12,22 * * *` | 02:20、12:20、22:20 |
| 6 | 化学9上每日教研 | chemistry / 9 / 人教版 | `25 2,12,22 * * *` | 02:25、12:25、22:25 |
| 7 | 生物7-8上每日教研 | biology / 7-8 / 人教版 | `30 2,12,22 * * *` | 02:30、12:30、22:30 |
| 8 | 历史7-9上每日教研 | history / 7-9 / 部编版 | `35 2,12,22 * * *` | 02:35、12:35、22:35 |
| 9 | 地理7-8上每日教研 | geography / 7-8 / 湘教版 | `40 2,12,22 * * *` | 02:40、12:40、22:40 |

> **班次口径（`01` / `02` 两份文件统一，按此读）**：`02` / `12` / `22` 是**逻辑班次标签**，只用于 `--shift` 取值、`tasks.json` 的班次策略、以及台账/日志里的班次标注，**不等于触发时刻**。
> - 上表右列仍是原文 cron 的钟点；`03-自动化注册清单.json` 里第三班实际写成 `BYHOUR=21`、`BYMINUTE=30..38`（21:30–21:38，按学科顺序每分钟一条），`--shift`/台账的班次 key 仍记 `22`（`tasks.json` 的 `shifts.22.label`＝「补漏班·前移至21:30」，仅作晚班逻辑标识），而载荷名按触发钟点写成 `-21点班`；前移理由与启用前提见 `00` 的调度章节与 `03` 的 `note`。
> - 因此 `-Shift 22`（或 `--shift 22`）表示「第三班的补漏职责」，不要求在 22:00 才动手；手动在任意时刻跑都合法，只要 `--date` 与班次职责对得上。
> - 本文件与 `01-主提示词.md` 是**会话直接照办的现行口径**（`run_all.*` 生成的提示词也以这两份为准），不是历史记录；历史变更、评审判定、验证记录只在 `00-CodeBuddy执行说明.md`，不要用那边的历史条目覆盖这两份现行规则。

## 生成侧结构硬约束（2026-11-11 定稿，9 段共用，各段末尾已各带一句）

来源是 11-11 那轮 31 册入库暴露的三个真问题，不是假想规则；违反任一条，数据在入库侧就是硬失败或制造垃圾节点。

| # | 约束 | 违反的后果 | 落地检查 |
|---|---|---|---|
| 1 | **知识点名唯一**：同一 `(学科, 年级, 知识点名)` 全库只能一个节点，本册内也不许重名/近似别名 | `import_content` 查到多个同名节点直接 `ValueError`，**整册导入中止**，同批其他年级一起被卡 | 生成前用 `context` 的「已用知识点名」比对；`validate` 通过后仍要人工扫一遍点名 |
| 2 | **禁止「样章·…」演示分组**：`section` 只能用本册真实章节名（取大纲 `chapters`） | 制造 0 题占位节点。11-07 遗留 55 组 / 165 节点就是这样来的，2026-11-11 才整棵删掉（`05` §5.x.7） | 点名里出现「样章」「示例」「演示」「占位」一律返工 |
| 3 | **point 必须挂 section**：`node_type='point'` 的 `parent` 非空且指向本文件已声明的 section | 悬空 point（全库曾出现 5 个，11-11 已归并）；导出/检索时层级断裂 | `validate` 报 parent 相关错误不许当提醒放过 |

补充口径：`section` 自身允许根级，**这不是缺陷**，不要为了让 hierarchy 好看而硬造一层假父节点（全库 556 个 section 现在全是根级，设计如此）。

---

## 1. 数学1-9上每日教研

```
$PY='D:\ai\prj\trae\HuaWei\AiLearning\backend\.venv\Scripts\python.exe'; $RUN='D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\_run_daily.py'
本次执行「数学1-9上每日教研」，班次 <02|12|22>，BATCH_DATE=触发当天 YYYYMMDD（全程不变）。
先读 D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\01-主提示词.md 全文并严格照办；参数以同目录 tasks.json 的 math 条为准。
固定：subject=math；数学；version=北师大版；semester=first（上册）；grades=1,2,3,4,5,6,7,8（按此顺序）；content_root=D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates。
大纲硬约束：baseline\_outline_math_first_latest.md 中本年级那一节；章节名用教材原名，order_index 取大纲序号；清单外不写，缺年级就停止并报告。
开工：& $PY $RUN plan --subject math --shift <班次> --date <BATCH_DATE> --json → idle 则只追加 idle_log_line 并结束；否则 lock acquire → 对 todos 逐年级 context → write_to_file 生成 JSON → validate → commit → finish。
边界：只产出 JSON + 追加台账/日志；不执行 import_content、不跑 --dry-run、不连数据库、不跑 alembic、不改已有文件、不读写其他学科文件；无可新增内容时台账记「无新增：原因」，不产空 JSON。硬约束：禁止调用 db_ops.py、禁止 ops.* / db_ops.py（run_all.* 已无入库 Action）、禁止任何入库或回退动作、禁止执行 ledger-sync / log-sync（人工运维命令，写动作均需 --confirm I_KNOW；_run_daily.py 已无 import/restore 子命令）。生成期约束：出题时就按住「每点 ≥4 题、难度 40/40/20 ±15pp」，分布不达标只能补题或换题，禁止事后批量调整已有题的 difficulty 凑比例。结构约束：本年级知识点名唯一且不与库内既有名重复（同名会让 import_content 抛 ValueError 中止整册）；section 只用本册真实章节名、禁止「样章·…」演示分组；point 的 parent 必须指向本文件已声明的 section、不得留空。
```

## 2. 语文1-9上每日教研

```
$PY='D:\ai\prj\trae\HuaWei\AiLearning\backend\.venv\Scripts\python.exe'; $RUN='D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\_run_daily.py'
本次执行「语文1-9上每日教研」，班次 <02|12|22>，BATCH_DATE=触发当天 YYYYMMDD（全程不变）。
先读 D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\01-主提示词.md 全文并严格照办；参数以同目录 tasks.json 的 chinese 条为准，并读 baseline\_chapters-baseline_latest.md 中语文 1-9 年级那几行。
固定：subject=chinese；语文；version=人教版；semester=first；grades=1..9（按此顺序）；大纲 baseline\_outline_chinese_first_latest.md 中本年级那一节。
学科要求：字词、古诗文、现代文阅读、写作素材分开覆盖；材料题材料自带；古诗文原文不得写错字；阅读题解析写清答题切入角度。
开工：& $PY $RUN plan --subject chinese --shift <班次> --date <BATCH_DATE> --json → idle 则只追加 idle_log_line 并结束；否则 lock acquire → 对 todos 逐年级 context → write_to_file 生成 JSON → validate → commit → finish。
边界：只产出 JSON + 追加台账/日志；不执行 import_content、不跑 --dry-run、不连数据库、不跑 alembic、不改已有文件、不读写其他学科文件；无可新增内容时台账记「无新增：原因」。硬约束：禁止调用 db_ops.py、禁止 ops.* / db_ops.py（run_all.* 已无入库 Action）、禁止任何入库或回退动作、禁止执行 ledger-sync / log-sync（人工运维命令，写动作均需 --confirm I_KNOW；_run_daily.py 已无 import/restore 子命令）。生成期约束：出题时就按住「每点 ≥4 题、难度 40/40/20 ±15pp」，分布不达标只能补题或换题，禁止事后批量调整已有题的 difficulty 凑比例。结构约束：本年级知识点名唯一且不与库内既有名重复（同名会让 import_content 抛 ValueError 中止整册）；section 只用本册真实章节名、禁止「样章·…」演示分组；point 的 parent 必须指向本文件已声明的 section、不得留空。
```

## 3. 英语1-9上每日教研

```
$PY='D:\ai\prj\trae\HuaWei\AiLearning\backend\.venv\Scripts\python.exe'; $RUN='D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\_run_daily.py'
本次执行「英语1-9上每日教研」，班次 <02|12|22>，BATCH_DATE=触发当天 YYYYMMDD（全程不变）。
先读 D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\01-主提示词.md 全文并严格照办；参数以同目录 tasks.json 的 english 条为准，并读 baseline\_chapters-baseline_latest.md 中英语 1-9 年级那几行。
固定：subject=english；英语；version=牛津深圳版；semester=first；grades=1..9；大纲 baseline\_outline_english_first_latest.md 中本年级那一节（英文原样、保留问号大小写；一个板块一天，做完一个单元再进下一个）。**英语 section 必须写「Unit N 标题 / 板块」复合名**（如 `Unit 1 What is your family like? / Ready Go`），point 的 parent 与它一致，chapters[].name 仍是完整单元名；纯板块名 `Ready Go` / `Story` 在多个单元重复，自检按 (单元,板块) 二元组校验并判 error，台账/日志的下一节计划也用复合名（大纲只有单元名的年级沿用单元名，不拼 `X / X`）。
学科要求：题干与选项用英文、解析用中文；不写依赖音频的听力题；覆盖词汇、语法、完形/阅读、写作四类；小学控词量，初中覆盖深圳中考常考语法（时态、被动、从句、非谓语）；多选解析逐项写 A/B/C/D 与 ✓/✗。
开工：& $PY $RUN plan --subject english --shift <班次> --date <BATCH_DATE> --json → idle 则只追加 idle_log_line 并结束；否则 lock acquire → 对 todos 逐年级 context → write_to_file 生成 JSON → validate → commit → finish。
边界：只产出 JSON + 追加台账/日志；不执行 import_content、不跑 --dry-run、不连数据库、不跑 alembic、不改已有文件、不读写其他学科文件；无可新增内容时台账记「无新增：原因」。硬约束：禁止调用 db_ops.py、禁止 ops.* / db_ops.py（run_all.* 已无入库 Action）、禁止任何入库或回退动作、禁止执行 ledger-sync / log-sync（人工运维命令，写动作均需 --confirm I_KNOW；_run_daily.py 已无 import/restore 子命令）。生成期约束：出题时就按住「每点 ≥4 题、难度 40/40/20 ±15pp」，分布不达标只能补题或换题，禁止事后批量调整已有题的 difficulty 凑比例。结构约束：本年级知识点名唯一且不与库内既有名重复（同名会让 import_content 抛 ValueError 中止整册）；section 只用本册真实章节名、禁止「样章·…」演示分组；point 的 parent 必须指向本文件已声明的 section、不得留空。
```

## 4. 道法1-9上每日教研

```
$PY='D:\ai\prj\trae\HuaWei\AiLearning\backend\.venv\Scripts\python.exe'; $RUN='D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\_run_daily.py'
本次执行「道法1-9上每日教研」，班次 <02|12|22>，BATCH_DATE=触发当天 YYYYMMDD（全程不变）。
先读 D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\01-主提示词.md 全文并严格照办；参数以同目录 tasks.json 的 politics 条为准，并读 baseline\_chapters-baseline_latest.md 中道法 1-9 年级那几行。
固定：subject=politics；道德与法治；version=部编版；semester=first；grades=1..9；大纲 baseline\_outline_politics_first_latest.md 中本年级那一节。
学科要求：小学与初中均写「道德与法治」，高中才叫「思想政治」；观点题材料自包含；法律条文只用教材表述，不引申、不评论；情境优先校园/家庭/深圳公共生活；多选解析逐项写 A/B/C/D 与 ✓/✗。
开工：& $PY $RUN plan --subject politics --shift <班次> --date <BATCH_DATE> --json → idle 则只追加 idle_log_line 并结束；否则 lock acquire → 对 todos 逐年级 context → write_to_file 生成 JSON → validate → commit → finish。
边界：只产出 JSON + 追加台账/日志；不执行 import_content、不跑 --dry-run、不连数据库、不跑 alembic、不改已有文件、不读写其他学科文件；无可新增内容时台账记「无新增：原因」。硬约束：禁止调用 db_ops.py、禁止 ops.* / db_ops.py（run_all.* 已无入库 Action）、禁止任何入库或回退动作、禁止执行 ledger-sync / log-sync（人工运维命令，写动作均需 --confirm I_KNOW；_run_daily.py 已无 import/restore 子命令）。生成期约束：出题时就按住「每点 ≥4 题、难度 40/40/20 ±15pp」，分布不达标只能补题或换题，禁止事后批量调整已有题的 difficulty 凑比例。结构约束：本年级知识点名唯一且不与库内既有名重复（同名会让 import_content 抛 ValueError 中止整册）；section 只用本册真实章节名、禁止「样章·…」演示分组；point 的 parent 必须指向本文件已声明的 section、不得留空。
```

## 5. 物理8-9上每日教研

```
$PY='D:\ai\prj\trae\HuaWei\AiLearning\backend\.venv\Scripts\python.exe'; $RUN='D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\_run_daily.py'
本次执行「物理8-9上每日教研」，班次 <02|12|22>，BATCH_DATE=触发当天 YYYYMMDD（全程不变）。
先读 D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\01-主提示词.md 全文并严格照办；参数以同目录 tasks.json 的 physics 条为准，并读 baseline\_chapters-baseline_latest.md 中物理 8-9 年级那几行。
固定：subject=physics；物理；version=人教版；semester=first；grades=8,9；仅 8-9 年级开设，其他年级跳过并报告；大纲 baseline\_outline_physics_first_latest.md 中本年级那一节（九年级为「全一册」，按章序正常推进，不要跳过后半册）。
学科要求：物理量带单位，计算题公式→代入→结果三步且结果带单位；不用看图题；实验题用文字描述器材与现象；数据取常见可核验值（g=10 N/kg，若用 9.8 需在题干说明）；多选解析逐项写 A/B/C/D 与 ✓/✗。
开工：& $PY $RUN plan --subject physics --shift <班次> --date <BATCH_DATE> --json → idle 则只追加 idle_log_line 并结束；否则 lock acquire → 对 todos 逐年级 context → write_to_file 生成 JSON → validate → commit → finish。
边界：只产出 JSON + 追加台账/日志；不执行 import_content、不跑 --dry-run、不连数据库、不跑 alembic、不改已有文件、不读写其他学科文件；无可新增内容时台账记「无新增：原因」。硬约束：禁止调用 db_ops.py、禁止 ops.* / db_ops.py（run_all.* 已无入库 Action）、禁止任何入库或回退动作、禁止执行 ledger-sync / log-sync（人工运维命令，写动作均需 --confirm I_KNOW；_run_daily.py 已无 import/restore 子命令）。生成期约束：出题时就按住「每点 ≥4 题、难度 40/40/20 ±15pp」，分布不达标只能补题或换题，禁止事后批量调整已有题的 difficulty 凑比例。结构约束：本年级知识点名唯一且不与库内既有名重复（同名会让 import_content 抛 ValueError 中止整册）；section 只用本册真实章节名、禁止「样章·…」演示分组；point 的 parent 必须指向本文件已声明的 section、不得留空。
```

## 6. 化学9上每日教研

```
$PY='D:\ai\prj\trae\HuaWei\AiLearning\backend\.venv\Scripts\python.exe'; $RUN='D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\_run_daily.py'
本次执行「化学9上每日教研」，班次 <02|12|22>，BATCH_DATE=触发当天 YYYYMMDD（全程不变）。
先读 D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\01-主提示词.md 全文并严格照办；参数以同目录 tasks.json 的 chemistry 条为准，并读 baseline\_chapters-baseline_latest.md 中化学 9 年级那几行。
固定：subject=chemistry；化学；version=人教版；semester=first；grades=9；化学仅 9 年级（初中）开设，其余年级跳过并汇报；大纲 baseline\_outline_chemistry_first_latest.md 中九年级那一节。
学科要求：化学式用纯文本（H2O、CO2、CaCO3），上下标不得用富文本；方程式配平并标条件（点燃/加热）；计算题写明相对原子质量取值；不用看图或读装置图的题；多选解析逐项写 A/B/C/D 与 ✓/✗。
开工：& $PY $RUN plan --subject chemistry --shift <班次> --date <BATCH_DATE> --json → idle 则只追加 idle_log_line 并结束；否则 lock acquire → 对 todos 逐年级 context → write_to_file 生成 JSON → validate → commit → finish。
边界：只产出 JSON + 追加台账/日志；不执行 import_content、不跑 --dry-run、不连数据库、不跑 alembic、不改已有文件、不读写其他学科文件；无可新增内容时台账记「无新增：原因」。硬约束：禁止调用 db_ops.py、禁止 ops.* / db_ops.py（run_all.* 已无入库 Action）、禁止任何入库或回退动作、禁止执行 ledger-sync / log-sync（人工运维命令，写动作均需 --confirm I_KNOW；_run_daily.py 已无 import/restore 子命令）。生成期约束：出题时就按住「每点 ≥4 题、难度 40/40/20 ±15pp」，分布不达标只能补题或换题，禁止事后批量调整已有题的 difficulty 凑比例。结构约束：本年级知识点名唯一且不与库内既有名重复（同名会让 import_content 抛 ValueError 中止整册）；section 只用本册真实章节名、禁止「样章·…」演示分组；point 的 parent 必须指向本文件已声明的 section、不得留空。
```

## 7. 生物7-8上每日教研

```
$PY='D:\ai\prj\trae\HuaWei\AiLearning\backend\.venv\Scripts\python.exe'; $RUN='D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\_run_daily.py'
本次执行「生物7-8上每日教研」，班次 <02|12|22>，BATCH_DATE=触发当天 YYYYMMDD（全程不变）。
先读 D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\01-主提示词.md 全文并严格照办；参数以同目录 tasks.json 的 biology 条为准，并读 baseline\_chapters-baseline_latest.md 中生物 7-8 年级那几行。
固定：subject=biology；生物；version=人教版；semester=first；grades=7,8；初中生物 7-8 开设，9 年级不开设；大纲 baseline\_outline_biology_first_latest.md 中本年级那一节（单元→章→节三级）。
学科要求：概念题与识图题不依赖图片，用文字描述结构；探究题写清变量控制与对照；生物名词用规范全称，首次出现可附简称；多选解析逐项写 A/B/C/D 与 ✓/✗。
开工：& $PY $RUN plan --subject biology --shift <班次> --date <BATCH_DATE> --json → idle 则只追加 idle_log_line 并结束；否则 lock acquire → 对 todos 逐年级 context → write_to_file 生成 JSON → validate → commit → finish。
边界：只产出 JSON + 追加台账/日志；不执行 import_content、不跑 --dry-run、不连数据库、不跑 alembic、不改已有文件、不读写其他学科文件；无可新增内容时台账记「无新增：原因」。硬约束：禁止调用 db_ops.py、禁止 ops.* / db_ops.py（run_all.* 已无入库 Action）、禁止任何入库或回退动作、禁止执行 ledger-sync / log-sync（人工运维命令，写动作均需 --confirm I_KNOW；_run_daily.py 已无 import/restore 子命令）。生成期约束：出题时就按住「每点 ≥4 题、难度 40/40/20 ±15pp」，分布不达标只能补题或换题，禁止事后批量调整已有题的 difficulty 凑比例。结构约束：本年级知识点名唯一且不与库内既有名重复（同名会让 import_content 抛 ValueError 中止整册）；section 只用本册真实章节名、禁止「样章·…」演示分组；point 的 parent 必须指向本文件已声明的 section、不得留空。
```

## 8. 历史7-9上每日教研

```
$PY='D:\ai\prj\trae\HuaWei\AiLearning\backend\.venv\Scripts\python.exe'; $RUN='D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\_run_daily.py'
本次执行「历史7-9上每日教研」，班次 <02|12|22>，BATCH_DATE=触发当天 YYYYMMDD（全程不变）。
先读 D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\01-主提示词.md 全文并严格照办；参数以同目录 tasks.json 的 history 条为准，并读 baseline\_chapters-baseline_latest.md 中历史 7-9 年级那几行。
固定：subject=history；历史；version=部编版；semester=first；grades=7,8,9；大纲 baseline\_outline_history_first_latest.md 中本年级那一节。
学科要求：时间、人物、事件、影响四要素准确；材料题材料自包含（引用原文 ≤150 字）；不得编造史料原文、年代或人物言论；评价只用主流教材口径，不做争议性引申。
开工：& $PY $RUN plan --subject history --shift <班次> --date <BATCH_DATE> --json → idle 则只追加 idle_log_line 并结束；否则 lock acquire → 对 todos 逐年级 context → write_to_file 生成 JSON → validate → commit → finish。
边界：只产出 JSON + 追加台账/日志；不执行 import_content、不跑 --dry-run、不连数据库、不跑 alembic、不改已有文件、不读写其他学科文件；无可新增内容时台账记「无新增：原因」。硬约束：禁止调用 db_ops.py、禁止 ops.* / db_ops.py（run_all.* 已无入库 Action）、禁止任何入库或回退动作、禁止执行 ledger-sync / log-sync（人工运维命令，写动作均需 --confirm I_KNOW；_run_daily.py 已无 import/restore 子命令）。生成期约束：出题时就按住「每点 ≥4 题、难度 40/40/20 ±15pp」，分布不达标只能补题或换题，禁止事后批量调整已有题的 difficulty 凑比例。结构约束：本年级知识点名唯一且不与库内既有名重复（同名会让 import_content 抛 ValueError 中止整册）；section 只用本册真实章节名、禁止「样章·…」演示分组；point 的 parent 必须指向本文件已声明的 section、不得留空。
```

## 9. 地理7-8上每日教研

```
$PY='D:\ai\prj\trae\HuaWei\AiLearning\backend\.venv\Scripts\python.exe'; $RUN='D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\_run_daily.py'
本次执行「地理7-8上每日教研」，班次 <02|12|22>，BATCH_DATE=触发当天 YYYYMMDD（全程不变）。
先读 D:\ai\prj\trae\HuaWei\AiLearning\docs\content-templates\exports\automation_20261108_codebuddy\01-主提示词.md 全文并严格照办；参数以同目录 tasks.json 的 geography 条为准，并读 baseline\_chapters-baseline_latest.md 中地理 7-8 年级那几行。
固定：subject=geography；地理；version=湘教版；semester=first；grades=7,8；大纲 baseline\_outline_geography_first_latest.md 中本年级那一节（章→节两级、无单元层）；高中地理 10-12「人教版」属另一条任务，不得越界。
学科要求：不依赖地图/景观图，经纬度、地形、气候信息用文字写进题干；可用深圳本地素材（气候、海岸线、台风、红树林）；数据必须真实可核验，拿不准不写具体数字。
开工：& $PY $RUN plan --subject geography --shift <班次> --date <BATCH_DATE> --json → idle 则只追加 idle_log_line 并结束；否则 lock acquire → 对 todos 逐年级 context → write_to_file 生成 JSON → validate → commit → finish。
边界：只产出 JSON + 追加台账/日志；不执行 import_content、不跑 --dry-run、不连数据库、不跑 alembic、不改已有文件、不读写其他学科文件；无可新增内容时台账记「无新增：原因」。硬约束：禁止调用 db_ops.py、禁止 ops.* / db_ops.py（run_all.* 已无入库 Action）、禁止任何入库或回退动作、禁止执行 ledger-sync / log-sync（人工运维命令，写动作均需 --confirm I_KNOW；_run_daily.py 已无 import/restore 子命令）。生成期约束：出题时就按住「每点 ≥4 题、难度 40/40/20 ±15pp」，分布不达标只能补题或换题，禁止事后批量调整已有题的 difficulty 凑比例。结构约束：本年级知识点名唯一且不与库内既有名重复（同名会让 import_content 抛 ValueError 中止整册）；section 只用本册真实章节名、禁止「样章·…」演示分组；point 的 parent 必须指向本文件已声明的 section、不得留空。
```

---

## 与原 query 的差异（逐条）

| 原文 | 改写后 |
|---|---|
| 「本次请求是由 X 定时任务到时触发的」 | 删掉触发态假设；班次与 BATCH_DATE 由 `--shift` / `--date` 显式传入，手动执行也能复现 |
| 「先读 _daily-task-instruction.md 全文，严格照其章节执行」 | 仍读它，但执行体改由 `01-主提示词.md` 映射到具体工具；`plan/context` 只给本年级所需片段，省上下文 |
| 「检查锁文件、判断 30 分钟、结束删锁」 | `lock --action acquire` / `finish` 原子完成，不靠模型读文本算时间 |
| 「跑 _validate_daily.py 带中文 --expect-version」 | `validate` 用参数列表调用，避开 PowerShell 中文引号与编码 |
| 「同名文件跳过、不重写、不加 _r2」 | `plan` 判存在、`write_to_file` 只写新文件、`commit` 拒绝覆盖 |
| 「台账追加 / 运行日志一行一个年级」 | `commit` 自动生成统计与日志行，`finish` 补收尾并释放锁 |
| 「运行环境=本地电脑 / runtime_type=2」 | 无需选择运行时；工作目录由 `cwds` 固定（见 03 文件） |
| 「6 字段 cron 一条任务三班」 | RRULE 单值 BYHOUR：每学科 3 条，共 27 条（见 03 文件） |
| 「按教材目录与 order_index 推进一个节，不跳章不重复」 | 原先靠模型读台账自行判断；现由 `progress_of()` 按大纲顺序 + 历史产出算出 `next_section`，写进 `plan` / `context` / `commit` 台账，避免无限停在同一节 |
