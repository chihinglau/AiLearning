# g1 / g8 上册全册评审 · 整改执行记录（2026-11-09）

范围：12 个「学科-年级」组合（math/chinese/english/politics × g1；math/chinese/english/politics/physics/biology/geography/history × g8），
共 77 个上册 JSON、70 个官方章。评审结论与 7 条建议已按用户「按你的建议执行吧」逐条落地。

## 一、评审核心结论（复述，未变）

1. **入库断链**：`daily\` 122 个 JSON，manifest 只登记 49 条，未登记 73 条（72 条是 `_rN` 分片）。
   生成侧 2078 题 → 库内 326 题，70 个官方章 **54 个 0 题（77%）**。math g8 / english g8 无 1108 主文件，1108 批次入库 0 条。
2. **颗粒度两套并存**：不带后缀的主文件 1 个「节」挂全单元；`_rN` 才是真实课时（每节 1~2 个知识点）。
3. **库内混入旧内容**：33 题（math g1 10 / chinese g1 9 / english g1 9 / physics g8 5）在任何 JSON 里找不到出处；
   math g8 / chinese g8 / english g8 三册库内内容全部来自 11-07 旧规格。
4. **台账指针失效**：4 册指针停在第 1 单元，分片已推进到全册；4 处章节序号回退。
5. **版本口径**：12 册版本不统一，`--expect-version` 写死「人教版」会让 6 组假红。

已确认**无问题**、不再复报：题量 18~28 全合规；难度配比 12 册全在 ±15pp（最大偏差 5pp）；
每题有答案+解析；0 重题、0 缺答案、0 缺解析、0 图依赖；五型齐备（多选键是 `multiple`）。

## 二、7 条建议的落地状态

| # | 建议 | 状态 | 产物 |
|---|---|---|---|
| ① | 一册一文件、禁 `_rN` | **已执行 `--apply`** | `daily_consolidated\` 12 册整册文件（1686 题，12/12 通过）；daily 原文件未动 |
| ② | 补分片归集器 | **已交付**（默认 dry-run，`--apply` 才写 `daily_consolidated\`） | `_consolidate_daily.py`；裁定规则「非 legacy > 批次最新 > 题量最多 > mtime 最新」；方案 `consolidation-plan_20261109.md/json` |
| ③ | 校验器补规格 fail | **已改并回归** | `_validate_daily.py`（新增 `check_spec()` + `--version-map` + `[分片]` 提醒 + 整册豁免）；导出包副本逐字节同步；旧版归档 `_archive\_validate_daily.frozen-20261109-2230.py` |
| ④ | 台账与生成联动 | **只读体检已交付，回写逻辑未做** | `_audit_ledger.py`；`ledger-audit_20261109.md`（4 处章节序号回退；11 册指针未随分片推进） |
| ⑤ | 库内清理（33 题无出处 + 3 册旧规格） | **清单 + 登记 + 回退脚本已出，库未动** | `05` §5.x.3/§5.x.4、`orphan-rollback-plan_20261109.md`、`orphan-rollback_20261109.sql`、`tasks.json` 的 `rerun_queue`(5) 与 `orphan_questions`(33 题) |
| ⑥ | 版本表落地 | **已建并实测生效，文档已补** | `baseline\_subject-version-map.json`；04 §3.8.1；与 `tasks.json.expected_version` 逐科核对一致 |
| ⑦ | 表述修订 | **已定位到题，未改文件** | `待修订内容清单.md` B 节（physics「金属块漂浮」、2 处算术解析、3 处多选逐项） |

## 三、新校验器回归结果（12 组实跑）

**改规格机检时：73 / 77 通过，4 个文件 5 处真错**（其余 8 组全绿）：

| 组 | 失败文件 | 错误 |
|---|---|---|
| chinese g8 | `chinese_g8_first_20261107.json` | 「新闻六要素」3 题、「电头与消息来源」1 题（规格 ≥4） |
| english g8 | `english_g8_first_20261107.json` | 「Water uses 水的用途」2 题 |
| politics g8 | `politics_g8_first_20261108_r3.json` | 空节「第三课共建网络美好家园」 |
| politics g8 | `politics_g8_first_20261108_r4.json` | 空节「第五课 社会生活讲道德」 |

> 这 4 个文件此前在旧校验器下是「0 错误」——规格机检把「声明了知识点却没挂够题」「空节」这两类盲区堵上了。
> **11-07 统一打标后**：前两个按 legacy 口径降级为提醒，**只剩 politics g8 的两个空节仍判错**，即 75 / 77。
> 整册文件另跑一轮：**12 / 12 全部通过**（整册豁免「每批次 3~6 知识点」，并已剔除那个空节）。

## 四、4 件待拍板事的执行结果（用户「1234都要做」→ 已全部落地）

1. **归集 `--apply` 已执行并已入库**：`daily_consolidated\` 下 12 册整册文件，**1686 题，12/12 通过校验器**；
   整库快照（`backend\_backup\ailearning_dev_20261109-043223.db`）后导入，`questions 957 → 2493`（净 +1536，先删了 33 题）、
   `knowledge_points 537 → 1120`；12 册上册 **0 空章**、0 缺答案/解析、`quick_check=ok`、外键 0 违规；留痕 `db_op_20261109_044100.json`。
   归集时踩到并修掉两个坑：整册若把全书知识点重新声明一遍，会被判「库内同名节点」（改为已存在的知识点不再声明，题目按旧名挂载）；
   复名知识点不声明后会出现「整册知识点全被跳过」的空节（改为连带剔除，并记进 `_consolidated.dropped_sections`）。
   整册文件**已登记 manifest 并已入库**（`db_op_20261109_044100.json`）；11-09 后续轮又补齐了入库入口（`db_ops.py import-books` / `ops.cmd -Action import-books`），
   因为 `-Action import -Date` 只扫 `daily` 目录树的 `*_<date>.json`，扫不到 `daily_consolidated` 的 `*_book.json`。
2. **13 个多版本章与 2 个越界章**：按规则各留一份，来源与理由逐章写进整册文件 `_consolidated.sources`；
   math g1「10以内加减法」、math g8「勾股定理」两处 legacy 旧样章**不并入整册**（记在 `_consolidated.outside_outline_skipped`）。
3. **33 题无出处 + 3 册旧规格**：逐题清单（id/章节/题干）`orphan-rollback-plan_20261109.md`、`policy.orphan_questions`（4 条 / 33 题）、
   回退 SQL `orphan-rollback_20261109.sql` **已按授权执行并复核剩余 0**（库 957 → 924）。~~58 题仍待拍板~~ →
   **2026-11-09 后续轮已清完**：按题干精确命中 11-07 旧文件后整批删除 math g8 `775–794`（20）+ chinese g8 `988–1007`（20）+ english g8 `1155–1172`（18），
   连同 1 组重复题（保留 `626`、删 `1227`）共删 **59 行**，`questions 2493 → 2434`；SQL 落盘
   `cleanup-legacy-duplicate_20261109.sql`，备份 `ailearning_dev_20261109-044016.db`，复核 `同章重题组 0` / `quick_check=ok` / 外键违规 0。
   三册改由整册文件提供题目（170 / 147 / 158 题、0 空章），`policy.rerun_queue` 已回落到 2 条（math g3 / g5）。详见 `05` §5.x.5。
4. **11-07 统一打标**：26 份 1107 文件全部带 `_legacy`（`mark_legacy_1107.py --apply`）。
   只加元数据键 → 内容哈希不变；manifest 只刷 `current_file_sha256`，三态仍是 `meta_only`（=已入库）。
   改前逐字节副本 `_archive\*.pre-legacy-mark.json`，留痕 `_archive\legacy-1107-mark.provenance.txt`。

**打标后的校验结果**：`daily\` 77 个文件 **75 通过 / 2 失败**——只剩 politics g8 `r3`、`r4` 的两个空节（1108 批次、非 legacy，是真缺陷）。

## 五、本轮未触碰的东西（可复核）

> 说明：本节记录的是**11-09 早轮**（只评审+清单）的边界；当天晚轮已按用户授权写库两次，见「六」。

- `daily\` 下 122 个 JSON：**除 18 份 1107 文件加 `_legacy` 元数据键外，内容一字未改**；
- `_import-manifest.json`：只刷了这 18 条的 `current_file_sha256`（条目数仍 49，imported_sha256 未动）；
- 数据库：全程只读（33 题清单、回退 SQL 均来自 `?mode=ro` 查询），**没有任何写库动作**；
- 历史 7 份 `db_op_*.json` 未改。

## 六、晚轮：库清理 + 知识点层清理（2026-11-09，两次真实写库）

1. **题目层**（`cleanup-legacy-duplicate_20261109.sql`）：删 1 组重复题（留 `626`、删 `1227`）+ 3 册 11-07 旧规格 58 题
   （math g8 `775–794`、chinese g8 `988–1007`、english g8 `1155–1172`），影响行数 1/20/20/18，复核 SELECT 返回 0 → COMMIT；
   `questions 2493 → 2434`；同章重题组 0、`quick_check=ok`、外键 0；备份 `ailearning_dev_20261109-044016.db`。
2. **知识点层**（`kp-cleanup_20261109.py` / `cleanup-kp-20261109.sql`）：删 9 个「样章·…」占位分组 + 18 子点（0 题 0 引用）；
   5 个实践类节点 `section → point`（清掉最后 5 道挂在 section 上的题）；2 个中文点名去 `?`；156 个 point 补 `prerequisites`；
   `knowledge_points 1120 → 1093`、`questions` 不变；备份 `ailearning_dev_20261109-050711.db`。
3. **基线同步**：新增 `_build_kp_baseline.py`（只读库重算），`baseline\_knowledge-points-baseline_latest.json/.md`
   改为 **703 个 point 名 / 0 歧义**（旧版 537 为部分口径），旧文件副本 `_archive\*.pre-kp-cleanup.*`。
4. **能力补齐**：`db_ops.py import-books` + `ops.cmd -Action import-books / import-books-dry` + `-Unattended`，
   解决「整册文件永远导不进库」的断点；`_consolidate_daily.py` 加 `--subjects/--grades/--semester/--stamp/--out-dir`，
   解决「只能归集 g1/g8 共 12 册」。两者均已实测（幂等 0 增量、`audit` diff 全 0）。

**仍未闭环**：其余 55 个「样章·…」占位知识点分组（g2–g7、g9–g12）；g1/g8 的 10 个空壳知识点待补题
（math g8 勾股定理 5 / chinese g8 新闻 5）；62 份 `_rN` 分片仍在 `daily` 未进 manifest；`_audit_ledger.py` 仍只读。
