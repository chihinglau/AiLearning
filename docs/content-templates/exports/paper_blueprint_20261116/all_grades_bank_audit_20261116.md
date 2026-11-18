# g1–g9 全学段组卷验收报告（2026-11-16）

> 范围：语文/数学/英语 × g1–g9 × 上下册 × 单元/期中/期末 = **162 条蓝图**
> 结论：**162/162 全部可出卷（100%）**，`pytest` 462 passed；自建题库累计 2322 题，占位选项 0、重复选项 0、answer 空值 0。

---

## 一、本轮新增（承接 g1 与 g2–g9 英语之后）

| 批次 | 内容 | 数量 | 脚本 |
|---|---|---|---|
| g2–g9 英语 | listening 976 / fill+choice+reading 732 / composition 48 | 1756 | `seed_english_bank_g2_g9.py` + `english_seeds_g2_g9.py` / `seed_data_lower.py` / `seed_data_upper.py` |
| g2–g9 语文 | 习作 48（16 册各 3 篇）+ 积累与运用填空 96（16 册各 6）+ 阅读简答 2 | 146 | `seed_chinese_bank_g2_g9.py` + `zh_compositions_g2_g9.py` / `zh_unit_fills_g2_g9.py` |
| g4–g9 数学 | 填空 18 + 计算解答 16 | 34 | `seed_math_supplement_g4_g9.py` |
| **合计本轮** | | **1936** | 另有 g1 386 题，总和 **2322** |

语文与数学的补充都锚定该册「第一单元」章节（`resolve_scope_chapters` 会把单元后的课级章节并入范围），所以一次补齐即可覆盖同册单元卷与期中/期末卷。

---

## 二、逐年级体检（`grade_paper_audit.py --export-docs`）

| 年级 | OK | 拒绝 | 语文 | 数学 | 英语 |
|---|---|---|---|---|---|
| g1 | 18 | 0 | 6/6 | 6/6 | 6/6 |
| g2 | 18 | 0 | 6/6 | 6/6 | 6/6 |
| g3 | 18 | 0 | 6/6 | 6/6 | 6/6 |
| g4 | 18 | 0 | 6/6 | 6/6 | 6/6 |
| g5 | 18 | 0 | 6/6 | 6/6 | 6/6 |
| g6 | 18 | 0 | 6/6 | 6/6 | 6/6 |
| g7 | 18 | 0 | 6/6 | 6/6 | 6/6 |
| g8 | 18 | 0 | 6/6 | 6/6 | 6/6 |
| g9 | 18 | 0 | 6/6 | 6/6 | 6/6 |

- 全部 `score_matches=True`：单元卷 语文 60 分 / 数学 60 分 / 英语 60 分；期中、期末 100 分。
- 题量：语文单元 15、期中期末 18；数学单元 12、期中期末 22；英语单元 28、期中期末 39。

---

## 三、三轮迭代轨迹（本轮）

| 阶段 | 可出卷 | 主要缺口 |
|---|---|---|
| g2–g9 英语铺完 + 语文习作入库前 | 96/162 | 语文 48 条全缺习作；数学 g4–g9 缺计算/填空 |
| 补 48 篇语文习作后 | 132/162 | 语文单元卷「积累与运用」填空不足（缺 1–4 题/卷）、g5 上期中缺 1 篇阅读简答 |
| 补语文填空 96 + 简答 2 + 数学 34 后 | **162/162** | — |

---

## 四、质量问题与修复

1. **英语占位选项**：初版干扰项池只有 2–3 条，245 道题退化成「以上都不是 / 信息不足」。改为 `REPLY_POOL`（12 条应答）+ `TOPIC_POOL`（14 个话题），`_choice` 固定 1 正确 + 3 干扰并按 seed 轮转。复检 2084 道英语自建题占位 0、重复 0。
2. **英语选项措辞不同构**：对话话题正确答案曾是「谈论「青少年生活」」，与干扰项「旅行」不对齐，统一为纯话题短语。
3. **语文单元卷被填空锁死**：语文章节原库每单元仅 4–6 道 fill，蓝图要 8 道，导致 16 条语文单元蓝图全部拒绝。补 6 道/册字词·古诗·句式填空后全部打通。
4. **数学 g4/g5 上册零计算解答**：该两册 answer 题型为 0，期中要 4 道「计算与证明」+ 2 道「综合应用」。补 6 道/册计算题（含长方形周长面积、三角形面积、小数乘除、分数应用）。

---

## 五、回归与库状态

- `pytest -o addopts='' -q --tb=line` → **462 passed, 1 warning, exit 0**（174s）。
- 落库前备份：`backend/build/backups/ailearning-backup-20261116-233230-pre-en-g2g9.db`（英语入库前；语文/数学补充为增量插入，未额外备份）。
- `selfbank` 明细：en_listen 976 / en_extra 732 / en_comp 48 / zh_comp 48 / zh_fill 96 / zh_answer 2 / math_supp 34 / 既有 g1 386。

---

## 六、已知不足（下一步）

1. **章节覆盖偏低**：期末卷覆盖 0.36–0.71（如 g4 数学上册期末 0.36、g2 语文下册期末 0.46）。原因是末几单元内容主要靠原库题支撑；若要抬到 0.8+，需按册补末 2–3 个单元的语料。
2. **英语 5 册期末覆盖 0.79–0.92**：补末章语料即可。
3. **习作评分点仍是 3 条通用维度**：低年级写话与中高年级议论文可用，若要贴近中考评分细则（内容/结构/语言各档）需细化。
4. 语文填空的「积累与运用」按册统一锚定第一单元，若要与真实单元课文严格对应，需按单元课文清单逐单元重写。

---

## 七、可复现命令

```powershell
Push-Location D:\ai\prj\trae\HuaWei\AiLearning\backend
$env:PYTHONPATH='D:\ai\prj\trae\HuaWei\AiLearning\backend'
& .venv\Scripts\python.exe scripts\seed_english_bank_g2_g9.py --grades 2 3 4 5 6 7 8 9 --apply
& .venv\Scripts\python.exe scripts\seed_chinese_bank_g2_g9.py --grades 2 3 4 5 6 7 8 9 --apply
& .venv\Scripts\python.exe scripts\seed_math_supplement_g4_g9.py --grades 4 5 6 7 8 9 --apply
& .venv\Scripts\python.exe scripts\grade_paper_audit.py --grade 8 --export-docs
Pop-Location
```

样卷落点：`docs/content-templates/exports/paper_blueprint_20261116/grade{1..9}_samples/<subject>_<semester>_<type>/`
