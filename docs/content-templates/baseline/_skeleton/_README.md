# 教材章节骨架导入批次（2026-11-07）

两套批次，目的都是让 App 切到某学期时**目录不空白**，只有章节名，无知识点、无题目。

| 批次 | 目录 | 文件/章节 | 用途 |
|---|---|---|---|
| 下册（推荐先导） | `baseline\_skeleton\` | 45 / **304** | 2027-02 起 App 自动切下册时的目录 |
| 上册（可选，用于替换「样章」） | `baseline\_skeleton_first\` | 45 / **300** | 导入后可安全删除 64 个「样章·…」占位章节 |

章节名与 `_outline_{subject}_{first,second}_latest.md` 完全同名，因此「库里章节名必须在大纲里」这条拦截天然成立；两个批次的 `semester` 分别是 `first` / `second`，互不影响。

## 执行命令（人工环节，在 `backend` 下，目标库由 `DATABASE_URL` 决定）

```powershell
# 0) 备份
.venv\Scripts\python.exe -m scripts.db_backup

# 1) 下册骨架
.venv\Scripts\python.exe -m scripts.import_content --path ..\docs\content-templates\baseline\_skeleton --dry-run
.venv\Scripts\python.exe -m scripts.import_content --path ..\docs\content-templates\baseline\_skeleton --manifest ..\docs\content-templates\_import-manifest.json

# 2) 上册骨架（EN: 若要清样章，先跑这一步）
.venv\Scripts\python.exe -m scripts.import_content --path ..\docs\content-templates\baseline\_skeleton_first --dry-run
.venv\Scripts\python.exe -m scripts.import_content --path ..\docs\content-templates\baseline\_skeleton_first --manifest ..\docs\content-templates\_import-manifest.json

# 3) 重建章节基线
.venv\Scripts\python.exe -m scripts.build_chapters_baseline --output-dir ..\docs\content-templates\baseline
```

幂等：同章节同名已存在时只更新 `order_index` / `summary`；manifest 按 sha256 跳过未变文件。

## 执行结果（2026-11-07 已全部执行完毕）

两套骨架已导入 **dev 与 device 两个库**，随后删除了全部占位章节。当前状态：

| 项 | dev | device |
|---|---|---|
| 教材 | 146 | 146 |
| 章节 | 643（上册 339 / 下册 304） | 638（上册 334 / 下册 304） |
| 知识点 | 382 | 337 |
| 题目 | 302 | 154 |
| 剩余「样章」 | 0 | 0 |

已删除：下册 g1-g3 语数英早期样例章节 27 个 + 108 题；「样章·…」占位章节 64 个 + 384 题。删除前备份：`ailearning_dev.db.bak-20261107-212118`、`ailearning_device.db.bak-20261107-212118`（三道引用表均为 0 引用才执行）。

导入过程中修掉导入器一个真实缺陷：`content_import.py` 第 254、336 行原来用 `data["knowledge"]` 直取，而 README 声明 `knowledge` 可省略，导致「只有章节、没有知识点」的骨架文件必然抛 `KeyError`。已改为 `data.get("knowledge") or []`。

### 仍然空的教材（已按 is_active 隐藏）

删除样章后，高中 10-12 全学科（54 本）没有任何章节。原因：自动化与大纲口径是 1-9 年级，高中数学/英语/地理用 `人教版A版`/`外研版`/`人教版`，从未做过高中大纲。

已用 `_deactivate_empty_textbooks.py` 把这 54 本置 `is_active=0` 隐藏，避免 App 出现空目录：

```powershell
python _deactivate_empty_textbooks.py            # 预览
python _deactivate_empty_textbooks.py --apply     # 执行（已执行）
python _deactivate_empty_textbooks.py --rollback  # 按清单恢复
```

停用清单：`baseline\_deactivated_textbooks_20261107.json`（两库各 54 条，含 id/subject/grade/version/semester）。回滚只按清单里的 id 置回 `is_active=1`，不影响其他教材。

**注意**：数学北师大版九年级上/下原本也被误停用（九年级学生选不到数学），已单独补齐：

- 大纲：`_outline_math_g9_first_latest.md` / `_outline_math_g9_second_latest.md`（各 7 章）
- 骨架：`baseline\_skeleton_math_g9\`（2 文件 / 14 章）
- 来源：`9s_2026/001.htm`（九年级上册 2026 秋版）、`9x/001.htm`（九年级下册）
- 这两册已恢复 `is_active=1` 并从停用清单移除

### 当前最终状态

| 项 | dev | device |
|---|---|---|
| 教材（启用 / 总数） | 92 / 146 | 92 / 146 |
| 启用教材中无章节 | 0 | 0 |
| 章节 | 657 | 652 |
| 知识点 | 382 | 337 |
| 题目 | 302 | 154 |
| 剩余「样章」 | 0 | 0 |

启用教材按年级：g1-g6 各 8 本、g7 14 本、g8 16 本、g9 14 本；g10-g12 全部停用。

**仍需你决定**：高中 10-12 若要支持，需要单独立项做 9 学科高中大纲（工作量约等于上册那套再做一遍）。

## 已知缺口

- 英语九年级下册 Unit 2 标题已补齐（`Finding balance in life`，来源：学科网 `docpack/3737725.html` 专辑目录），九下 6 个单元齐全。
- 二年级下册英语来源为教习网课文目录，建议开学前用实体书核对。
- 数学 3-6 下册只有单元级，无课时级节名。

## 2026-11-14 骨架纠偏（physics g9 上下册同名同章）

**问题**：统一骨架索引 `exports/review_20261112/rerun_skeleton_index_g1g9_unified_20261113.json` 里 physics g9 下册的 `source` 指向 `_skeleton\chapters_physics_g9_second_20261107.json`，但 `chapters` 数组与上册**逐字相同**（第十三章 内能 … 第二十二章 能源与可持续发展，10 章），即下册套用了上册的章列表；内容包侧 `physics_g9_second.py` 也随之写了同一批 10 章，造成同一学期两册覆盖同一批章节。

**修正**（按人教版九年级物理实际分册）：

| 册 | 修正前 | 修正后 |
|---|---|---|
| physics g9 上册 | 10 章（13–22） | **6 章**：第十三章 内能、第十四章 内能的利用、第十五章 电流和电路、第十六章 电压 电阻、第十七章 欧姆定律、第十八章 电功率 |
| physics g9 下册 | 10 章（13–22，与上册同） | **4 章**：第十九章 生活用电、第二十章 电与磁、第二十一章 电磁波及其应用、第二十二章 能源与可持续发展 |

- 骨架侧：`_fix_skeleton_physics_g9.py` 改 `chapters / chapter_count / source / note`，原文件备份 `rerun_skeleton_index_g1g9_unified_20261113_bak_20261114120640.json`；
- 组装侧：`_rerun_books.py` 的 `CHAPTER_SCOPE` + `apply_chapter_scope()`（在 `load_packs` 阶段裁剪，自检与校验器都按裁剪后的章名比对）；
- 库侧：`_scope_cleanup.py`（先删题目再删章节）删除「文件已无、库内仍留」的章节，本轮删 10 章 / 192 题；
- 基线变化：92 册不变，章节 **618 → 608**、知识点声明 **2472 → 2432**、题目 **11870 → 11678**；
- 参照范式：化学 g9 分册本就正确（上册 7 章 = 第一～七单元，下册 4 章 = 第八～十一单元），新增册拆上下册时照此对齐。

> 语文各年级「第一/二…单元」、数学 g4/g5/g6「总复习」在上下册同名属教材真实结构（章属于不同 textbook），**不要**当缺陷改名。

## 重新生成

```powershell
python _build_chapters_skeleton_second.py second
python _build_chapters_skeleton_second.py first
python _validate_daily.py baseline\_skeleton --kp-baseline baseline\_knowledge-points-baseline_latest.json
python _validate_daily.py baseline\_skeleton_first --kp-baseline baseline\_knowledge-points-baseline_latest.json
```
