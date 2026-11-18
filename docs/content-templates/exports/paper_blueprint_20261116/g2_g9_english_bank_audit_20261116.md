# g2–g9 英语自建题型题库铺量验收报告（2026-11-16）

> 范围：牛津深圳版英语 g2–g9 共 16 册、122 个具名单元章节；投料 1756 题；目标为解锁 48 条英语蓝图（8 年级 × 上下册 × 单元/期中/期末）。
> 结论：**48/48 全部可出卷（100%）**，`pytest` 462 passed；占位选项 0、重复选项 0。

---

## 一、入库明细

| source_ref 前缀 | 题型 | 数量 | 说明 |
|---|---|---|---|
| `selfbank:en_listen` | listening | 976 | 122 章 × 8 题（词辨识 2 / 句中关键词 2 / 问句应答 2 / 对话话题 2），带 `script` 供教师版朗读 |
| `selfbank:en_extra` | fill + choice + reading | 732 | 122 章 × 6 题（填空 2 / 情景单选 2 / 阅读 2）；难度 3/5/4，落在 medium、hard 带 |
| `selfbank:en_comp` | composition | 48 | 16 册 × 3 篇，含 `title`、`min_words`、3 条评分点、范文 |
| **合计** | | **1756** | 另有 g1 英语 328 题，`selfbank:en_*` 累计 2084 题 |

数据源：`backend/scripts/english_seeds_g2_g9.py`（汇总入口）+ `seed_data_lower.py`（g2–g5，68 章）+ `seed_data_upper.py`（g6–g9，54 章）。
生成器：`backend/scripts/seed_english_bank_g2_g9.py`，`--grades` + `--apply`/`--dry-run`，`source_ref` 幂等。
落库前备份：`backend/build/backups/ailearning-backup-20261116-233230-pre-en-g2g9.db`。

---

## 二、体检结果（`grade_paper_audit.py`）

| 年级 | 英语 6 套 | 单元卷题量 | 期中/期末题量 | 章节覆盖（最低） |
|---|---|---|---|---|
| g2 | 6/6 OK | 28/28 | 39/39 | 0.90（下册期末） |
| g3 | 6/6 OK | 28/28 | 39/39 | 0.89 |
| g4 | 6/6 OK | 28/28 | 39/39 | 0.91 |
| g5 | 6/6 OK | 28/28 | 39/39 | 0.79（下册期末） |
| g6 | 6/6 OK | 28/28 | 39/39 | 0.79（下册期末） |
| g7 | 6/6 OK | 28/28 | 39/39 | 0.92 |
| g8 | 6/6 OK | 28/28 | 39/39 | 0.96（下册期末恰为 1.00） |
| g9 | 6/6 OK | 28/28 | 39/39 | 0.89 |

- 全部 `score_matches=True`：单元卷 60 分、期中/期末 100 分，与蓝图分值逐项对齐。
- 未通过项全部是语文（g2/g3 各 6 条、g4–g9 各 8 条），原因是缺 `composition`（习作），属下一阶段任务；数学在 g2–g3 已 6/6，g4–g9 仍有单元/期中供给缺口。

---

## 三、本轮修掉的两个质量问题

1. **占位选项**：初版干扰项池只有 2 条（问句应答）与 3 条（话题类），4 选项凑不满就退化成「以上都不是 / 信息不足」。改为全局 `REPLY_POOL`（12 条日常应答）与 `TOPIC_POOL`（14 个话题），并把 `_choice` 固定裁剪为 1 正确 + 3 干扰（按 `start` 轮转去偏移）。复检：**2084 题中占位 0、重复 0**。
2. **选项措辞不一致**：对话话题题的正确答案写成「谈论「青少年生活」」，与干扰项「旅行」不同构。已统一为纯话题短语。

重建方式：先按 `source_ref like 'selfbank:en_%'` + `chapter_id in SEEDS` 精确清理 g2–g9（不动 g1 的 328 题），再 `--apply` 重灌，两次均为 1756 题、0 跳过。

---

## 四、回归

`pytest -o addopts='' -q --tb=line` → **462 passed, 1 warning, exit 0**（耗时 172s）。

---

## 五、下一步（按用户排序）

1. **语文 g1–g9 习作与字词填空**：g2/g3 各 6 条、g4–g9 各 8 条蓝图待解锁，须按年级分体裁给评分点（低年级写话 3–5 句，中高年级记叙/说明/读后感）。
2. **数学 g4–g9 单元与期中供给**：g4/g5 缺口最大，按每册补 20 题 choice/fill 推进。
3. 英语章节覆盖 0.79–0.92 的 5 册期末卷，可再补 2–3 个末章语料抬到 0.95+。

---

## 六、可复现命令

```powershell
Push-Location D:\ai\prj\trae\HuaWei\AiLearning\backend
$env:PYTHONPATH='D:\ai\prj\trae\HuaWei\AiLearning\backend'
& .venv\Scripts\python.exe scripts\seed_english_bank_g2_g9.py --grades 2 3 4 5 6 7 8 9 --dry-run
& .venv\Scripts\python.exe scripts\seed_english_bank_g2_g9.py --grades 2 3 4 5 6 7 8 9 --apply
& .venv\Scripts\python.exe scripts\grade_paper_audit.py --grade 8 --export-docs
Pop-Location
```

样卷落点：`docs/content-templates/exports/paper_blueprint_20261116/grade{2..9}_samples/english_{first|second}_{unit|midterm|final}/`
