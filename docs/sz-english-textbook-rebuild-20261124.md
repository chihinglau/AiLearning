# 英语 7/8/9 年级（上下册）教材与题库重建（2026-11-24）

## 结论

库内英语原来用的是**牛津上海版（五四学制、上海本地用）6 单元目录**，与深圳在用的**沪教牛津版（2024）深广版 8 单元**不符，孩子同步巩固练的是上海的单元。本轮已按深圳版大纲把 7/8/9 年级六个学期的章节、知识点、题目整体重建（九下因大纲未发布改为占位章），并把全库英语教材版本名统一改成「沪教牛津版（2024）·深圳」，库、仓库文档、校验参数、cron 任务参数四处同一口径。上册三册已在真机（xuanxuan / 初中 8 年级上学期）验收通过。

## 单元对照（旧 → 新）

### 8 年级上册（67）

| 旧（牛津上海版 6 单元） | 新（深广版 8 单元） |
|---|---|
| Unit 1 Water | Unit 1 Look it up! |
| Unit 2 Digital life | Unit 2 Amazing numbers |
| Unit 3 Curious minds | Unit 3 Our digital lives |
| Unit 4 Then and now | Unit 4 Inventions |
| Unit 5 Teamwork | Unit 5 Going on an exchange trip |
| Unit 6 Life in the future | Unit 6 Wisdom counts |
| — | Unit 7 The secret of memory |
| — | Unit 8 Pets and us |

### 8 年级下册（68）

旧：Art and artists / Festival / Science and technology / Traditional skills / Problems and worries / Friendship
新：Helping those in need / Body language / Comics and animation / Arts and heritage / Saving animals in danger / Learning by doing / Space exploration / Imagine that!

### 7 年级上册（53）

旧：Trying new things / Strong mind / Jobs / Smart home / Films / Mountains and rivers
新：Friendship / School life / The seasons / The Earth / Off to space / Travelling around Asia / Fun after school / Collecting as a hobby

### 7 年级下册（54）

旧：Unit 1 Music / … / Unit 6 Trees
新：People around us / Travelling around the world / Trees and us / Our animal friends / Water / Electricity / Poems / From hobby to career

### 9 年级上册（83）

旧：Teenage life / People and their jobs / Travellers' tales / Folk customs / Buildings / Pollution
新：Great people / Great ideas / Family traditions / A better me / My time, my joy / Food and health / Reading Mark Twain / The power of love

### 9 年级下册（84）

上教版新教材九年级下册官方目录未发布，本轮不编造单元：合并为一个占位章「待发布·上教版新教材九年级下册」（is_placeholder=1、0 题），旧上海版 6 章及其 291 道题全部下线。

## 具体动作

1. 章节原地换名（保留 chapter_id 与 textbook_bindings，xuanxuan 的 english=67 不变），上册与八下补齐到 8 个单元、order_index 1–8；「样章·Grammar in use」占位章移到末位（53→7、67→9、83→7）。
2. 知识点按单元重建：每单元 1 个 section + 4 个 point（词汇 / 语法 / 功能 / 写作），复用旧知识点行改名而非删除，保住了 101 行 `mastery_scores` 的个体掌握度统计。
3. 题库按新单元重铺：每单元 25 题（单选 8 + 词汇填空 2 + 语法单选 4 + 语法填空 4 + 判断 3 + 多选 2 + 简答 2），五册共 1000 题；旧单元题（53 册 294、54 册 274、67 册 291、68 册 268、83 册 312、84 册 291）已下线，不再出现「章节换了题还是旧的」。
4. 题干英文、解析中文，多选解析逐项写 A/B/C/D 与 ✓/✗；不写依赖音频的听力题。
5. 结构自检 0 问题：五册 40 个单元、每单元 25 题、选项键无重复、答案键均存在于选项、解析无空；`GET /api/public/chapters?textbook_id=68` 返回 8 个新单元名。

## 版本名成套收口

- 旧串 `上教版（沪教牛津深圳版）` → 新串 `沪教牛津版（2024）·深圳`。
- 库：`textbooks.version` 英语 18 行（1–9 年级上下册）全部更新。
- 仓库：23 个含旧串的文件同步替换，含 `_daily-task-instruction.md`、两份 outline baseline、`_chapters-baseline_latest.md`、`rerun_packs/_PACK_SPEC.md`、当日 g1–g3 教研 JSON 与台账、`align_sz_curriculum.py`、`english_by_unit_data.py`、`app_constants.dart`。
- 校验：`_validate_daily.py daily\english\g1\english_g1_first_20261124.json --expect-version 沪教牛津版（2024）·深圳` → 通过，EXIT=0。
- cron：任务「英语1-9上每日教研」query 内 `version=` 与 `--expect-version` 两处已改为新串，调度（`10 2,12,22 * * *`，Asia/Shanghai）与标题未动。

## 真机验收（xuanxuan / 初中 8 年级上学期）

- 学科浮层：英语「沪教牛津版（2024）·深圳 · 8 年级 · 上学期」（重启 App 后实拍确认，版本名已随库更新生效）。
- 同步巩固·英语 20 题预览：知识点覆盖 19/42、单选 9 / 判断 2 / 多选 3 / 填空 2 / 听力 4。
- 第 1 题：`A dictionary ___ you the meaning of words.`（Unit 1 Look it up! 语法点「一般现在时第三人称单数」）→ 选 B. tells，反馈「回答正确 · 正确答案 B. tells · 解析：主语 A dictionary 是第三人称单数，一般现在时动词加 -s · 掌握度 60 分」。

## 未动 / 待办

- 七下、八下重建与九下占位未做真机卷面抽检（上册已验），App 单元列表对九下「待发布…」的呈现也待看。
- 早前遗留的 dev 库测试账号（tester2026 / stuxuan2026 / kidconsent01 / xiaoxue2026 / kidui2026）未清理。
- 备份：`backend/ailearning_dev.db.bak-20261124-before-en-rebuild`。
