# 英语 7/8/9 年级上册教材与题库重建（2026-11-24）

## 结论

库内 7 年级上册（textbook_id 53）、8 年级上册（67）、9 年级上册（83）原来用的是**牛津上海版（五四学制、上海本地用）**6 单元目录，与深圳在用的**沪教牛津版（2024）深广版 8 单元**不符，孩子的同步巩固练的就是上海的单元。本轮已按深圳版大纲把章节、知识点、题目整体重建，并在真机（xuanxuan 账号 / 初中 8 年级上学期）验收通过。

## 重建前 → 重建后

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

### 7 年级上册（53）

旧：Trying new things / Strong mind / Jobs / Smart home / Films / Mountains and rivers
新：Friendship / School life / The seasons / The Earth / Off to space / Travelling around Asia / Fun after school / Collecting as a hobby

### 9 年级上册（83）

旧：Teenage life / People and their jobs / Travellers' tales / Folk customs / Buildings / Pollution
新：Great people / Great ideas / Family traditions / A better me / My time, my joy / Food and health / Reading Mark Twain / The power of love

## 具体动作

1. 章节原地换名（保留 chapter_id 与 textbook_bindings，xuanxuan 的 english=67 不变），每册补齐到 8 个单元、order_index 1–8；「样章·Grammar in use」占位章移到末位（order_index 9）。
2. 知识点按单元重建：每单元 1 个 section + 4 个 point（词汇 / 语法 / 功能 / 写作），复用旧知识点行以免影响已有个体掌握度记录。
3. 题库按新单元重铺：每单元 25 题（单选 8 + 词汇填空 2 + 语法单选 4 + 语法填空 4 + 判断 3 + 多选 2 + 简答 2），三册共 600 题；旧上海版单元题（53 册 294 题、67 册 291 题、83 册 312 题）已下线，不再出现「章节换了题还是旧的」。
4. 题干英文、解析中文，多选解析逐项写 A/B/C/D 与 ✓/✗；不写依赖音频的听力题。
5. 结构自检 0 问题：三册 24 个单元、每单元 25 题、选项键无重复、答案键均存在于选项、解析无空。

## 真机验收（xuanxuan / 初中 8 年级上学期）

- 学科浮层：英语「上教版（沪教牛津深圳版） · 8 年级 · 上学期」。
- 同步巩固·英语 20 题预览：知识点覆盖 19/42、单选 9 / 判断 2 / 多选 3 / 填空 2 / 听力 4。
- 第 1 题：`A dictionary ___ you the meaning of words.`（Unit 1 Look it up! 语法点「一般现在时第三人称单数」）→ 选 B. tells，反馈「回答正确 · 正确答案 B. tells · 解析：主语 A dictionary 是第三人称单数，一般现在时动词加 -s · 掌握度 60 分」。

## 未动 / 待办

- **下册（54 七下 / 68 八下 / 84 九下）仍是上海版 6 单元**：属于 2027 春季学期在用书，本轮未改，留待春季前按同一模式重建（八下 Help those in need 8 单元、七下 People around us 8 单元已在大纲基线中）。
- 版本名仍保留「上教版（沪教牛津深圳版）」：与每日教研流水线、导入校验、cron 任务参数里的 `--expect-version 上教版（沪教牛津深圳版）` 保持同一口径；若要改成「沪教牛津版（2024）·深圳」，需同时改库、大纲基线、校验脚本参数与 cron 任务参数，一次成套改，单独改库会让入库校验失配。
- 备份：`backend/ailearning_dev.db.bak-20261124-before-en-rebuild`。
