# 真机走查报告：考试中心与作答页（EBG-AN00）

- 走查日期：2026-11-18
- 走查对象：9 年级 × 3 科目 × 3 阶段 = 81 张自建题库组卷（dev 库 exam id 14–94）
- 设备：HUAWEI EBG-AN00（product/model `EBG-AN00`，serial `2NSDU20423005421`，Android 12，1080×2340 @480dpi）
- 客户端：`com.ailearning.ai_learning` `app-debug.apk`（157,912,402 B，构建于 2026-11-17 00:11:12，含当日最新前端代码）
- 连通方式：`adb reverse tcp:18080 tcp:18080` → 本机 uvicorn `127.0.0.1:18080`
- 学生账号：`13900000000 / student123`（「小深」，student，走查起始 grade=1，结尾已恢复 grade=1）
- 截图证据目录：`docs/content-templates/shots/ebg/`
- 全量审计数据：`docs/content-templates/exports/ui_audit_20261118/{paper_ui_audit.csv, issue_detail.csv}`
- 审计脚本：`backend/scripts/audit_walkthrough_papers_ui.py`；造卷脚本 `backend/scripts/gen_walkthrough_papers.py`

---

## 一、结论摘要

81 张卷**全部生成成功且结构正确**（题量、满分、大题分组与蓝图 100% 一致），问题集中在三类：**英语听力不可作答（P0）**、**卷面内容规范（P1）**、**学生端交互与信息呈现（P1/P2）**。

| 级别 | 条数 | 涉及卷 | 说明 |
|---|---:|---:|---|
| P0 | 252 | 27（全部英语卷） | 听力题无任何音频字段，学生无法作答 |
| P1 | 142 | 41 | 同卷重题 83、习作无要求 54、答案入题干 4、选项重复 1 |
| P2 | 60 | — | 填空题干无作答空位 |
| **合计** | **454** | **63 / 81** | 18 张卷结构层面零问题 |

> 上表是**修复前**的口径（2026-11-18 01:00）。修复后为 **58 条、P0 归零、51/81 卷全净**，见第八节；第三节各表同样是修复前基线，不要与修复后数字混读。

另发现 9 项**代码级缺陷**（不在上述 454 条数据审计内），其中 2 项直接影响可用性：底部操作栏命中区偏移、考试中心筛选与列表手势间歇性无响应。

**一句话结论**：题库内容侧已达「可展示」水平，但**英语卷目前给学生做是不能及的**（听力板块 252 题全空），且作答页存在按不准、点不动的手感问题，需在修复 P0 后才能进入验收。

---

## 二、真机渲染走查（逐屏证据）

| # | 场景 | 截图 | 观察结论 |
|---|---|---|---|
| 1 | 学生登录后学习页 | `22_relaunch.png` | 身份「小学·1年级·上学期」，登录态重启保持 |
| 2 | 待办考试（g1） | `23_entry_pos.png` | 3 张英语走查卷正确出现；**标题被截断为「1年级英语期末走查卷（自建…」** |
| 3 | 考试中心入口 | `23_entry_pos.png` | 副标题「3 场考试待完成」，与实际 9 张待办不符 |
| 4 | 考试中心筛选器 | `36_center_again.png` | 4 组筛选占首屏约 80%，列表只能露出 1 张卡的一半 |
| 5 | 英语期末卷第 1 题 | `24_en_final_enter.png` | `第 1 / 39 题 · 单选题 · 2 分`，大题「一、听力」，题干「听录音，选出最合适的应答」，**无播放控件** |
| 6 | 英语期末卷阅读题 | `26_en_q11b.png` | `第 34 / 39 题`，英文短文 + 题干 + 4 选项，排版正常 |
| 7 | 英语期末卷第 35 题 | `34_btn_edge.png` | 「阅读短文，选出短文中出现内容的中文意思。短文：I am fine…」，**阅读理解退化为单词翻译** |
| 8 | 语文单元卷第 1 题 | `42_zh_final_q1.png` | 填空题 `2 分`，「"人"字共有（ ）笔。」+「请在此填写答案」输入框，答题卡 15 格完整可见 |
| 9 | 语文单元卷版面 | `42_zh_final_q1.png` | 短题干下答题卡下方约 500px 空白，内容不居中 |
| 10 | 跨年级 g5 学习页 | `46_g5_home.png` | 切库 `grade=5` 后首页显示「5 年级·上学期」，今日计划同步刷新 |
| 11 | g5 待办 | `47_g5_entry.png` | 待办全为 5 年级英语三卷，年级过滤正确 |
| 12 | g5 卷列表 | `48_g5_center.png` | 数学单元 12 题/60、语文期末 28 题/100、语文期中 24 题/100、语文单元 15 题/60，与蓝图一致 |
| 13 | g5 数学单元第 1 题 | `49_g5_math_q1.png` | `单选题 · 4 分`，「计算3.6加2.7，结果是（ ）」A6.3/B6.13/C5.3/D5.13，渲染正常 |
| 14 | 列表手势 | `44_math_list.png` → `45_math_find.png` | 两次上滑列表无位移，滚动失效 |
| 15 | 历史测试卷 | `45_math_find.png` | 卷名直接为「**153**」，副信息「期末·语文·18题·满分100」 |
| 16 | 旧演示卷口径 | `19_center_refresh.png` | 「深圳市一年级数学期末模拟卷（2025）」标 **满分 58**；「剩余 0 分钟，点击继续作答」与「共 3 次作答」并存 |

---

## 三、数据侧全量审计（81 张，100% 覆盖）

脚本对每张卷的每一道题做了 9 条规则判定（题干、题型、选项、答案、分值、大题、重复），结果如下。

### 3.1 规则分布

| 规则 | 判定内容 | 级别 | 条数 | 涉及卷 |
|---|---|---:|---:|---:|
| LR-1 | 听力题无音频字段 | P0 | 252 | 27（英语全部） |
| LR-6 | 同卷题干重复 | P1 | 83 | 26 |
| LR-4 | 习作题无字数/要求 | P1 | 54 | 54（语英各 27） |
| LR-5 | 答案原文出现在题干 | P1 | 4 | 4 |
| LR-2 | 选项文本重复 | P1 | 1 | 1 |
| LR-3 | 填空题干无作答空位 | P2 | 60 | 22 |

### 3.2 结构正确性（全部通过）

| 检查项 | 结果 |
|---|---|
| 题量与蓝图一致 | 81 / 81 |
| 小题分值合计 = 卷面满分 | 81 / 81（如 g1 语文单元 60.0/60、g1 英语期末 100.0/100） |
| 大题（section）分组存在 | 81 / 81（3–5 个：单元 3–4 个、期中/期末 4–5 个） |
| 题号连续、section_name 正确 | 81 / 81 |

### 3.3 典型问题样本（逐条已回表核对）

**LR-6 同卷重题**（exam 14，g1 语文单元）：

> 第 3 题与第 9 题题干完全相同：「在括号里填上合适的量词：一（　）纸。」

成因：组卷 `avoid_recent_repeats` 与卷内去重都按 `question_id` 判定，**库内存在同题干不同 id 的重复题**，需按题干指纹（去空格/标点后 hash）去重。

**LR-5 答案入题干**（exam 25，g2 语文期末第 9 题）：

> 题干：「曹冲用（　）代替大象，称出石头就有大象的重量。」　答案：「石头」——答案词已在后半句出现，且句子逻辑不通顺。

**LR-2 选项重复**（exam 36，g3 数学期中第 10 题）：两个选项文本同为 `3/6`。

**LR-4 习作无要求**：全部语文/英语卷的习作题均未写「不少于 N 字」，与中考语文作文「内容/结构/语言」分档评分不对齐。

---

## 四、代码级缺陷清单（含证据行号）

| 编号 | 级别 | 缺陷 | 证据（文件:行号 / 截图） | 整改建议 |
|---|---|---|---|---|
| D-1 | **P0** | 英语听力题无音频、无播放控件，学生无法作答 | `backend/app/models/content.py:47-76`（`Question` 无 audio/media 列）；`backend/scripts/audit_walkthrough_papers_ui.py` LR-1 命中 252 题；`shots/ebg/24_en_final_enter.png` | 三选一：(a) `Question.content` 增加 `audio_url` 并补音频资产；(b) `content.meta` 约定 `audio_url` + 作答页渲染播放器；(c) 在补齐音频前，把 listening 题型从自建卷蓝图 `_SECTIONS` 中停用，避免出「无法作答」的卷 |
| D-2 | **P1**→已修复 | 作答页底部按钮实测高度仅 38dp，下沿贴到全面屏手势区，同一屏 y=2165/2135 点不动、y=2105 才生效 | `app/lib/features/exam/exam_page.dart:527`、`:839-878`；`shots/ebg/24_en_final_enter.png`、`32_press.png` | 已固定 52dp 命中高度并显式并入手势区高度（见第八节），新版真机按钮整栏可点 |
| D-3 | ~~P1~~ 撤销 | 考试中心筛选项「点击无响应」——**复核为走查坐标误差，非缺陷** | `shots/ebg/37_filter_chinese.png`、`38_filter_retry.png`；复核依据见第八节 uiautomator bounds | 无需修改代码 |
| D-4 | ~~P1~~ 撤销 | 考试中心列表「上滑无位移」——**复核为同一原因，非缺陷** | `shots/ebg/44_math_list.png`、`45_math_find.png`；复核见第八节 | 无需修改代码 |
| D-5 | **P1** | 待办计数「N 场考试待完成」与实际待考数量不符（g1 显示 3，实际 9） | `backend/app/services/recommendation.py:321`（`limit: int = 3`）、`:361`（`if len(result) >= limit: break`）；`app/lib/features/learn/learn_page.dart:410`（用 `pendingExams.length` 当总数）；`shots/ebg/23_entry_pos.png` | 服务端在 `HomeOut.pending_exams` 增补 `pending_total` 字段，前端用它显示总数、用前 3 条做预览 |
| D-6 | **P1** | 待办卡片标题单行截断，卷名主体丢失（显示到「（自建…」） | `app/lib/widgets/feature_card.dart:78`（`maxLines: 1` + `ellipsis`）；`shots/ebg/23_entry_pos.png`、`47_g5_entry.png` | 标题改 `maxLines: 2`，或把「（自建题库）」这类后缀从 title 移到 subtitle |
| D-7 | **P2** | 39 题卷答题卡超出屏幕，下半部分（29–39）被裁切，必须滚动才能点 | `app/lib/features/exam/exam_page.dart:619-624`（`_AnswerSheet` 直接放在 `SingleChildScrollView` 内容流里）；`shots/ebg/24_en_final_enter.png` | 答题卡改为可折叠浮层/底部抽屉，或限制可见行数 + 内部滚动 |
| D-8 | **P2** | 短题干页面底部约 500px 空白，内容不居中、信息密度低 | `app/lib/features/exam/exam_page.dart:590-637`（`SingleChildScrollView` + `Column`）；`shots/ebg/42_zh_final_q1.png` | 内容区加 `ConstrainedBox`/`IntrinsicHeight` 处理，或把答题卡与保存提示贴近内容 |
| D-9 | **P2** | 历史测试卷数据污染学生视图：卷名「153」、旧演示卷「满分 58」与蓝图 100 不符、「剩余 0 分钟…点击继续作答」与「共 3 次作答」文案矛盾 | 数据侧（dev 库既有 exam 记录）；`shots/ebg/45_math_find.png`、`19_center_refresh.png` | 清理 dev 库历史演示卷，或在列表层过滤 `source='demo'` 且 title 为纯数字的卷 |

> 说明：D-3/D-4 最初判为「真机手势间歇失效」，经 uiautomator 取到 Flutter 语义树真实 bounds 后**撤销**——`语文` chip 实际位于 `[403,834][590,978]`，而当时点击的 (540,690) 落在 chip 之间的空白区；列表上滑则在精确坐标下正常位移。原因是截图高 2340 而 Flutter 视图区只有 2202（差 138px），叠加 chip 间 8dp 间隙，坐标估算偏了。这一条要记住：**在 EBG 上定位控件必须先 dump bounds，不能按截图目测**。

---

## 五、覆盖范围与限制（如实说明）

**真机逐屏覆盖**：g1 英语期末（听力 + 阅读）、g1 语文单元（填空 + 答题卡）、g5 数学单元（单选）、考试中心列表/待办/筛选、跨年级（g1→g5）切换。

**未真机逐张打开的部分**：g1 语文/数学余下 7 张、g2–g9 的 72 张。原因是 D-3/D-4 的手势间歇失效使「逐张进入—翻题—截图」的流程不可靠（同一坐标时灵时不灵），继续投入的边际收益低于修复后再走查。这部分由第三节的结构审计**全量覆盖**（81 张、1708 道题 100% 读到题干/选项/答案）。

**跨年级走查方式**：临时改 `User.grade`（1→5→1）而非另造 9 个分年级账号；学生列表按 `Exam.grade == current.grade` 过滤（`backend/app/api/routes/exams.py:585-586`、`:1049-1050`），因此跨年级必须切账号年级。测试账号 `13900000000` 已于走查结束恢复 `grade=1`。

**发现但归属内容侧（重复作业）**：g1 英语第 35 题「阅读短文，选出短文中出现内容的中文意思」把阅读理解做成了单词翻译，短文仅 3 句不连贯语句；g5 数学第 1 题「计算3.6加2.7」口语化、且单选题干又留了「（　）」空位，卷面冗余。这两类属题库用语/题型设计规范，建议并入下一轮内容治理。

---

## 六、整改清单（按顺序执行）

| 序 | 动作 | 责任面 | 验收口径 |
|---:|---|---|---|
| 1 | 决策听力题处置方案（补音频 / 约定 audio_url 渲染 / 暂停 listening 出题） | 产品 + 后端 | 英语 27 张卷不再出现「听录音」但无播放控件的题；LR-1 归零 |
| 2 | 修底部操作栏命中区（D-2） | 前端 | 真机上按钮上下边缘 8px 内均可点，翻题 39 题全程无卡顿 |
| 3 | 复现并修筛选/列表手势（D-3、D-4） | 前端 | 连续点 3 组筛选各 1 次均生效；列表 3 次上滑均有位移 |
| 4 | 卷内重题按题干指纹去重（LR-6） | 后端组卷 | 81 张卷 LR-6 归零 |
| 5 | 习作题补字数与写作要求（LR-4） | 内容教研 | 54 道习作题均含「不少于 N 字」与文体提示 |
| 6 | 补 `pending_total` 修计数（D-5）、标题两行（D-6） | 后端 + 前端 | 待办计数 = 实际待考数；标题完整可读 |
| 7 | 清理 60 处填空题干无空位（LR-3）、4 处答案入题干（LR-5）、1 处选项重复（LR-2） | 内容教研 | 对应规则归零 |
| 8 | 答题卡可折叠（D-7）、短题干版面（D-8） | 前端 | 39 题卷答题卡一屏可见或可折叠 |
| 9 | 清理 dev 历史演示卷（D-9） | 测试/运维 | 学生列表无「153」类标题、无满分口径冲突 |
| 10 | 修完 1–3 后，按本报告口径**重跑一遍逐张真机走查** | QA | 81 张逐张进入并翻至末题，截图归档 |

---

## 七、走查数据处置

> 更新（2026-11-18 03:05）：`--clean` 走的是 `DELETE /api/exams/{id}`，该路由**不存在**（返回 405），一轮下来只清 0 张，而「旧卷没删 + 新卷 avoid_recent_repeats」直接把题池占满，导致 g1/g4–g9 语文单元、g5–g9 数学单元共 11 张回「题量不足」被拒。已改为直接操作 dev 库删除（`ExamAttempt` 一并清），首次清理实为 **150 张**（之前多轮生成有累积）。gen 脚本的 `--clean` 分支需要改成走库或补 DELETE 路由。

81 张走查卷（id 14–94，`published`）当前留在 dev 库，会污染学生考试中心列表。清理方式（DB 直删，脚本见 `%TEMP%\clean_walk.py` 思路，或修好 `--clean` 后再用）：

```powershell
Push-Location D:\ai\prj\trae\HuaWei\AiLearning\backend
$env:PYTHONPATH='D:\ai\prj\trae\HuaWei\AiLearning\backend'
& .venv\Scripts\python.exe scripts\gen_walkthrough_papers.py --apply
```

（81 张 / 0 失败，约 3 分钟。）

---

## 八、修复与验证（2026-11-18 02:10–03:10）

### 8.1 先纠正一条走查方法结论：flutter 工具链是可用的

上一轮判定「flutter 跑不起来（`WHERE` not recognized / `Unable to find git`）」是**错的**。真实原因是执行环境的 `PATH` 被裁掉了 `C:\Windows\System32` 与 Git 目录，`flutter.bat` 依赖的 `where.exe`、`git.exe` 找不到。补回 PATH 并指定 `JAVA_HOME` 后：

- `flutter --version` → `Flutter 3.41.10-ohos-1.0.1`
- `flutter analyze` → `No issues found!`
- `flutter build apk --debug` → **32.6s 构建成功**

所以本轮所有前端缺陷都是「改了、重编了、真机装上了、真机验过了」，不再是纸面建议。

可用构建命令（下次直接用）：

```powershell
$env:PATH = "C:\Windows\System32;C:\Windows;C:\Program Files\Git\cmd;D:\ai\prj\trae\HuaWei\MyLangLean\.tools\jdk17\jdk-17.0.2\bin;" + $env:PATH
$env:JAVA_HOME='D:\ai\prj\trae\HuaWei\MyLangLean\.tools\jdk17\jdk-17.0.2'
$env:ANDROID_HOME='D:\ai\prj\trae\HuaWei\MyLangLean\.tools\android-sdk'
Push-Location D:\ai\prj\trae\HuaWei\AiLearning\app
& 'D:\ai\prj\trae\HuaWei\MyLangLean\.tools\flutter_ohos\bin\flutter.bat' build apk --debug
```

### 8.2 已修七项，逐项真机验证

| 项 | 改动 | 证据 |
|---|---|---|
| D-1 听力不可作答 | 蓝图 `LISTENING_AS_CHOICE=True` 开关：英语分节「一、听力」等题量等分改为「一、基础选择」（choice），题量/总分不变；题库 listening 数据不动，音频资产到位后置 False 即恢复；`apply_matrix` 已同步 81 条蓝图 | 审计 LR-1 `252 → 0`；`g1_english_final` sections 实测为 `一、基础选择 choice 10×2 … 总分 100` |
| LR-6 同卷重题 | `exam_paper.py` 新增 `stem_fingerprint()`（去空白/标点的题干指纹），`_pick()` 增加卷级 `seen_stems`，跨大题传递 | 审计 LR-6 `83 → 0`（exam14 q3/q9 同类不再出现） |
| LR-2 选项重复 | 随组卷重跑自然消除 | LR-2 `1 → 0` |
| LR-4 习作无字数 | 236 道习作题统一在题干尾部补「（不少于 N 字/词）」，N 取题库存量 `content.min_words`（语英分别用字/词）；备份 `ailearning-backup-20261118-023402-pre-compword.db` | LR-4 `54 → 0`（其中 45 条真补，8 条为规则过严误判，见 8.4） |
| D-5 待办计数 | 后端 `collect_pending_exams()` 返回全量、`HomeOut.pending_exams_total` 新增字段；前端 `learn.dart` 增 `pendingExamsTotal`，`learn_page.dart:410` 改用该字段 | 接口实测 `pending_exams_total=12 / len=3`；真机首页显示「**12 场考试待完成**」（原 3） |
| D-6 标题截断 | `feature_card.dart:78` `maxLines: 1 → 2` | 真机标题完整显示「1年级英语期末走查卷（自建题库）」 |
| D-7 答题卡被裁 | `_AnswerSheet` 改 StatefulWidget，默认只展示 12 格（两行）+「展开全部 39 题」 | 真机 39 题卷第 2 题：两行答题卡 + 展开按钮，不再被屏底裁掉 |

截图：`shots/ebg/51_fix_home.png`（计数 12 + 标题两行）、`52_fix_answer_page.png`（答题卡折叠 + 52dp 底部栏）。

### 8.3 修复后的全量审计（口径一致，脚本同一份）

| 规则 | 修复前 | 修复后 | 说明 |
|---|---:|---:|---|
| LR-1 听力无音频 | 252 (P0) | **0** | 蓝图不再出 listening 题 |
| LR-6 同卷重题 | 83 (P1) | **0** | 题干指纹去重生效 |
| LR-4 习作无字数 | 54 (P1) | **0** | 补字数 + 规则修正（8 条误判） |
| LR-5 答案入题干 | 4 (P1) | **1** | 剩 exam53 q6「答案 4元 出现在题干」，需教研改写，未动 |
| LR-2 选项重复 | 1 (P1) | **0** | 重跑自然消除 |
| LR-3 填空无空位 | 60 (P2) | **57** | 题干无「（　）」类空位；学生端仍有输入框，属卷面规范，未批量改（改题干易伤语义） |
| **合计** | **454** | **58 → 5** | P0：252 → 0；全净卷 18 → 51 → **76 / 81** |

导出：`docs/content-templates/exports/ui_audit_20261118_after_fix/{paper_ui_audit.csv, issue_detail.csv}`（修复前口径快照保留在 `ui_audit_20261118_after_fix` 上一级目录的旧文件已被覆盖，修复前数字以第三节表格与本表「修复前」列为准）。

### 8.4 必须说明的口径调整（没有变好的地方不要算成变好）

LR-4 从 54 降到 0，其中 **8 条不是内容改善，是我这条审计规则过严**：原规则除了「是否写了字数要求」，还把「题干短于 25 字」直接记 P1，于是英语「用 6 句话写…（不少于 35 词）」明明已给篇幅要求仍被判缺陷。已把长度改为兜底判据（<12 字才判无要求），并补入「不少于 N 词」的正则。**所以这 8 条的消失来自规则修正，不来自题库改写**——不含它的真实改善是 46 条。

同理，LR-3 只从 60 掉到 57 是随机组卷换了几道题，不代表问题在缓解；57 条仍在。

### 8.5 环境侧两个坑（下次别踩）

1. **后端存在两个 uvicorn 同时绑 18080**（venv 的和系统 Python 的），改了代码仍返回旧字段，就是这个原因。已统一停掉，只留 `backend\.venv` + `--reload` 一个实例（`app.main:app`，cwd=backend）。
2. `gen_walkthrough_papers.py --clean` 依赖的 `DELETE /api/exams/{id}` 不存在（405），清理必须走库。

### 8.6 修复后仍未解决（移交下一轮）

- **题库里 236 道 listening 题**依然是「无音频」状态，只是不再进卷。要真正恢复听力，需要 `Question.audio_url`（或 `content.meta.audio_url`）+ 逐题音频资产 + 作答页播放控件，三件套齐了再把 `LISTENING_AS_CHOICE` 置 False。
- ~~答题页「退出无二次确认、返回后倒计时重置」未动。~~ → 已在 **8.8（1）（2）** 处理：退出确认已实现并真机验证；「倒计时重置」经实测为误判，已撤销。
- ~~历史演示卷「153」「满分 58」等脏数据仍在库里，未清理。~~ → 已在 **8.8（3）** 处置：3 张早期演示脏卷统一置 `status='offline'`（不删、不改分，保留历史作答）。

### 8.7 第三轮：题库内容治理（LR-3 / LR-5 / LR-2）

原以为剩下的 58 条只能靠教研逐条改，实际拆开看，**大部分仍是审计规则与题库口径对不上**，可机器处理：

| 规则 | 剩 58 条时的判断 | 查清后的真相 | 处置 |
|---|---|---|---|
| LR-3 填空无空位 57 | 以为题干真没留空 | 语文 23 条写的是「画蛇添__」（双下划线），英语 25 条写的是「（写英文）」——都在正常交代作答位，是判据只认 `____` 与空括号 | 判据改为「任意下划线 / 任意括号」；另把全库真正没空位的 **90 道**（数学 76、英语 12、政治 1、语文 1）在句末补「（　）」→ 全库 4,774 道填空题 **100% 有作答位** |
| LR-5 答案入题干 4→1 | 以为是个别题写漏 | 全库 220 道题在题干里直接写「（填「光照」）」把答案送出去；另有大量「2.4元」含「4元」这类子串重叠被误判 | 清掉 220 条「（填「X」）」提示（备份 `…-pre-answerhint.db`）；判据排除数字型答案；剩 99 条需教研复核，导出 `exports/answer_leak_review.csv`（含 38 条引用原文型，已标注豁免理由） |
| LR-2 选项重复 1 | 随机现象 | 全库 5,938 道选择题只有 **2 道**重复（分数题 19322/19323，如 C/D 都是「5/10」，正确答案还写成「1/1」） | 已重写两组选项并校正答案（`1/3+2/3=1`）→ 全库选项重复 **0 道** |

**最终状态**：454 → **5 条**，P0 始终为 0，全净卷 76/81。且这 5 条全部是 LR-5，**每轮重新组卷后条数在 0–5 之间漂移**（上一轮 2 条、再上一轮 4 条），原因是随机抽到「引用原文的默写题」——例如「有的人活着，他已经死了；有的人死了，他还（　）」答案「活着」，题干必须引用原文，这不属于提示泄露。真正的提示型泄露（「（填「X」）」）已归零。

**所以这一项不再追零**：继续追只会和随机性搏斗，剩下的应交教研按 `answer_leak_review.csv` 的 99 条「需复核」逐条判断要不要改写题干。

### 8.8 第四轮：退出确认 / 倒计时证伪 / 脏卷下架 / 新缺陷 D-9

本轮补做 8.6 遗留项，并在真机上逐条留证。设备 EBG-AN00（1080×2340，Android 12），学生「小深」（grade=1 上学期），`adb reverse tcp:18080`。

**（1）退出无二次确认 —— 已修**

`exam_page.dart` 新增 `bool _allowPop`，`build` 改为 `PopScope(canPop: _allowPop || _loading || _error != null, onPopInvokedWithResult: … _confirmExit(), child: _buildScaffold(...))`；`_confirmExit` 确认后置 `_allowPop = true` 再 `context.pop()`。

真机结果（截图 `shots/ebg/53_reentry_timer.png` 为同轮取证）：

| 操作 | 观测 |
|---|---|
| 进入 1 年级英语期末走查卷 | 倒计时 **89:52** |
| 静置 12 秒 | 倒计时 **89:30**（正常递减） |
| 按系统返回键 `keyevent 4` | 弹「**退出考试？**」「退出后计时不会暂停，已作答内容会自动保存，可在考试中心继续作答。」+「继续考试」「退出」 |
| 点「退出」 | 回到列表，无白屏、无丢作答 |

**（2）「返回后倒计时重置」—— 判定为误判，撤销**

之前把它写进 8.6，本轮实测不成立：

| 时点 | 倒计时 |
|---|---|
| 首次进入 | 89:52 |
| 12 秒后 | 89:30 |
| 退出确认后点「退出」，再重进同一卷 | **88:46**（不是 90:00） |
| 稍后再从考试中心「继续作答」进入 | **85:45**，再 23 秒后 **85:22** |
| 考试中心列表显示该卷 | 「进行中 · 剩余 85 分钟，点击继续作答」 |

根因在服务端：`_remaining_seconds()` 由 `attempt.started_at` 与 `time_limit_min` 推算，`/start` 对 `in_progress` 且 remaining > 0 的 attempt 直接复用、不改 `started_at`，客户端只做展示，因此不存在重置路径。此前判「重置」是把「首次进入未走满一刻钟」误读成归零。

**（3）历史脏卷 —— 置 offline，不删**

扫全库 94 张卷的分值合计，全部一致，唯 3 张为早期演示遗留：id1「深圳市一年级数学期末模拟卷（2025）」24 题 58 分（有 3 条作答记录）、id3「…三年级数学期末模拟卷（2024）」24 题 58 分、id8 标题就是「153」18 题 100 分。三张统一 `status='offline'`：**不删、不改分**，学生端不再出现，历史作答记录保留。published 由 93 → 90。

**（4）新缺陷 D-9：习作题被标成「单选题」—— 已修并复验**

真机点进语文卷第 28/28 题，题干「如果让你当一天家，你会做哪些事？写一写你的安排（不少于 70 字）」正常，但题型行写的是「**单选题 · 30 分**」。属题型中英映射缺分支：`composition` 落进 `default`，而 `default` 返回「单选题」。

修法：3 处 `_typeLabel` 同时补分支，并把兜底从「单选题」改成「本题」——认不出类型时不该替学生假定题式。

| 文件 | 位置 | 改动 |
|---|---|---|
| `app/lib/features/exam/exam_page.dart` | `_typeLabel`（约 :919–941） | 补 `composition/essay/writing → 习作题`、`choice → 单选题`，`default → 本题` |
| `app/lib/features/exam/exam_report_page.dart` | `_typeLabel`（约 :578–589） | 同上 |
| `app/lib/features/session/session_page.dart` | `_typeLabel`（约 :744–755） | 同上，另补 `listen → 听力题` |

`app/lib/core/models/learn.dart` 的 `KpExample.typeLabel` 兜底本就是 `return qType`，不改；`practice_config_page.dart` 的 `_qTypeLabels` 是配置页固定选项，暂不动。

复验：`flutter analyze` → No issues found；`flutter build apk --debug` 成功（12s 内）；`adb install -r -d` Success 后重进同一卷第 28 题，题型行变为「**第 28 / 28 题 · 习作题 · 30 分**」（截图 `shots/ebg/55_q28_typefixed.png`）。

> 过程记录：第一次改 `exam_page.dart` 时替换 switch 尾部漏了三个闭合花括号，`flutter analyze` 报 `exam_page.dart:1149 expected_token`、`gradle assembleDebug` 失败。补回后通过。Dart 的 `Edit` 改 switch 尾必须跑一次 `analyze` 再打包。

**（5）题库大改后的真机渲染抽检（补齐 8.7 的落地验证）**

8.7 清了 220 条「（填「X」）」并给 90 道填空补了「（　）」，本轮在真机上确认改动是可见且正确的：

| 检查点 | 观测 |
|---|---|
| 语文卷第 1 题（填空·2 分） | 「「多」的反义词是（ ）。」—— 空位渲染正常，不为空、不吞括号 |
| 语文卷第 28 题（习作·30 分） | 「……（不少于 70 字）」字数要求完整显示，题型修正后为「习作题」 |
| 英语期末卷第 1 题 | 节标题为「**一、基础选择**」（题库 listening 降级为 choice 生效），题干与 A/B/C 选项完整 |
| 答题卡 | 折叠态显示「展开全部 28 题」；展开后格 28 可点并跳转；展开后出现「收起」 |

**本轮结论**：8.6 列的三项遗留（退出确认、倒计时误判、脏卷）已闭环；新发现并关闭 1 项（D-9）。学生端可正常完成「进入 → 作答 → 退出确认 → 继续作答」闭环，倒计时按服务端 `started_at` 连续计时。

### 8.9 第五轮：读题（TTS）在考试页的缺失 —— 已补齐（CR-007）

用户反馈「docs 设计文档原本是低年级语文/数学读题 + 全年龄英语读题，现在 app 功能好像被改没了」。本轮先做「是否被删」的核实，再做补齐。

**（1）核实：功能没被删，缺口是两处**

| 检查项 | 结果 |
|---|---|
| `core/speech/question_speech.dart`、`tts_service.dart`、`speech_settings.dart` | 在位 |
| `features/speech/speech_button.dart`、`features/speech/readable_question_text.dart` | 在位 |
| `core/speech/question_audio.dart`、`question_reader.dart`（设计后追加的音频优先 + 缓存） | 在位 |
| `pubspec.yaml:20` `flutter_tts: ^4.2.5` | 在位 |
| `app/test/question_speech_test.dart` | 在位 |
| git 删除提交 | 无（唯一相关提交 `541bc29 feat(tts): …`） |
| `session_page.dart` / `practice_page.dart` 读题引用数 | 各 14 处 |
| `exam_page.dart` / `exam_report_page.dart` 读题引用数 | **0 处** |

两处真实缺口：① 门禁写死 `grade 1..3` 且限 `{chinese, math, english}`（`session_page.dart:642`、`practice_page.dart:241`），4–9 年级英语没有喇叭；② `exam_page.dart` 从未接入读题——学生在考试中心卷子上看不到喇叭，这就是「感觉被改没了」的直接来源。

**（2）修法**

| 文件 | 改动 |
|---|---|
| 新增 `app/lib/core/speech/speech_policy.dart` | `enabled({grade, subject})`：英语任意年级为真；非英语须 1–3 年级且属语文/数学/英语；科目 trim+lowercase 容错；`autoReadByDefault({grade})` 仅 1–3 |
| 新增 `app/test/speech_policy_test.dart` | 7 例，锁定范围不再被收窄 |
| `session_page.dart`、`practice_page.dart` | `_speechEnabled` 改调 `SpeechPolicy.enabled` |
| `exam_page.dart` | 题干改 `Row` + `ReadableQuestionText` + `SpeechButton`；新增 `_speechEnabled` / `_stopSpeaking` / `_goTo`；上一题、下一题、答题卡三处切题统一走 `_goTo`（先停读再切）；`_confirmExit` 与 `dispose` 补停读 |
| `learning_settings_page.dart` | 两段说明文案改为「…以及各年级英语题目，都可点击题干右侧的喇叭朗读」 |

考试页**刻意不做自动朗读**：计时中突然出声会干扰考场秩序，只保留手动喇叭；练习/复习页的自动读题不变。

**（3）真机复验（EBG-AN00，`adb reverse tcp:18080`）**

| 场景 | 观测 | 判定 |
|---|---|---|
| g1 英语单元走查卷（考试页第 1/28 题） | 题干右侧「朗读题目」`[936,492][1032,588]`；英文题干按单词切成可点节点（`Read` / `the` / `passage`），说明单词点读生效 | 通过 |
| 点击该喇叭 | 按钮变「停止朗读」；logcat `AudioTrack: start(1566)`、`AudioPlayerStateMonitor … content=CONTENT_TYPE_SPEECH … state:started` | 通过（真出声） |
| g8 英语期末走查卷（账号 `grade` 临时改 8，第 1/39 题） | 同样出现「朗读题目」；点击后 `TtsSystemService: onSynthesizeText lang=eng` → `AudioTrack start` | 通过（后端无该年级预生成音频，走系统 TTS 兜底，无 404 报错、无等待） |
| g8 语文期末走查卷（第 1/28 题，填空） | **无喇叭**（题干区只有题干与答题卡） | 通过（4–9 语文仍不开放，符合口径） |
| 账号恢复 | `users.grade` 8 → 1，重启 app 后回到 1 年级教材与待办 | 已恢复 |

**（4）遗留与说明**

1. 4–9 年级英语音质为系统 TTS（各机型音色不一），低于 1–3 年级语数英的 Piper 预生成音频；若要统一音质，需按 CR 评估扩产（涉及合成体积与人工抽检）。
2. `flutter analyze` 0 issue、`flutter test test/speech_policy_test.dart` 7 passed、`flutter build apk --debug` 27.7s 成功，均已在本轮执行。
3. 环境坑重演一次：进卷时出现「交卷已暂存到本地 / 当前网络不可用」，排查为后端 uvicorn 进程已退出（18080 无监听、`/health` 拒绝连接）；重拉后端后恢复。此前「看不到喇叭」若在这种状态下观测，会被误判成读题没接上——**先查 `/health` 再判断 UI**。



---

### 附：CR-008 听力题真机走查（2026-11-18 第二轮）

**（1）观测对象与现象**

- 试卷：EBG-AN00 学生端「1年级英语期中走查卷（自建题库）」，第 1/39 题为听力题（题型标注「听力题 · 2 分」，大题「一、听力」，题干「听录音，选出与录音内容一致的单词。」，选项 happy / tall / short / clean）。
- 现象：题干右侧有耳机图标；点击 (988,462)/(986,460)/(960,462)/(1015,462)/(950,462) 多轮多坐标，**始终无 `/audio` 请求、`dumpsys audio` 无播放器、无 SnackBar**。
- 对照实验：同一页面点选项 A（300,800）→ 答题卡由 0/39 变 1/39、A 变蓝，证明坐标系与整页触摸链路正常。

**（2）两个被证伪的假设**

| 假设 | 证伪方式 | 结论 |
|---|---|---|
| 后端没出听力题（组卷缺听力） | 直打 `POST /api/learn/practice/preview`（chapter 219 / count 10 / special / q_types 含 listening），**20 次随机 seed 全部含 listening 2–3 道** | 排除；卷子里确实有听力题 |
| 配置页 chips「无听力」 | 「单选 2 / 单选 4 / 填空 3 / 判断 1」实为 `listening 2 + choice 4 + fill 3 + judge 1`，`_shortTypeLabel` 把 listening 落进 `default → '单选'` | 是标签 bug，非缺题 |
| 图标太小 / 新码未装 | 32×32 `InkResponse` → 48dp `IconButton` 后图标位置由 (988,460) 移到 (952,462)，证明新码生效，但点击仍无响应 | 尺寸不是根因，**Row 内 hit-test 被题干 `Expanded` 挤占** |

**（3）最终形态与验证**

- 听力题播放入口改为题干下方整行左侧的大按钮「🔊 播放听力材料」（`OutlinedButton.icon`，高 44dp；播放中显示「停止播放」）；非听力题仍是题干右侧喇叭。三处作答页（exam / session / practice）统一。
- 真机验证：

| 场景 | 观测 | 判定 |
|---|---|---|
| 期中卷作答页（第 2/39 题）点「播放听力材料」 | uvicorn 立即出现 `GET /api/learn/questions/15795/audio?speed=1.0&kind=listening HTTP/1.1" 200 OK` | 通过（真播放） |
| 练习页 Unit 1 综合练习（第 1/10 题，听力题） | 进入即自动播放，按钮直接显示「停止播放」 | 通过 |
| 配置页组卷预览 chips | 「听力 2 · 判断 1 · 单选 4 · 多选 2 · 填空 1」 | 通过（标签修复生效） |

**（4）本轮结论**

听力题在 EBG-AN00 上「能出、能播、能作答」三条链路全部打通；**遗留**：听力播放次数限制（防重播）尚未做，需后端 attempt 记账，客户端限制防不住 force-stop 重进。

---

## 九、2026-11-19 全年级复验（g1–g9 × 语文/数学/英语 × 三阶段）

> 前八节集中在 g9 与单点验证；本节把范围推到全年级，并把「库里有卷」升级为「每张卷都能开考、都能读」。

### 9.1 方法

逐年级把学生 `grade` 切到 g1–g9，重启 App、滚动两次进入考试中心，每个年级截「首屏 + 下滑屏」共 **18 张**，逐张判读卷名 / 学科 / 题量 / 满分 / 时限，与后端 `GET /api/exams` 的返回逐项对照；再对 81 张卷跑一次真实开考（`POST /api/exams/{id}/attempts`）。

### 9.2 结果

| 项 | 结果 |
|---|---|
| 目录形态（卷名/学科/题量/满分/时限） | 9 个年级 × 9 张卷全部与接口一致，无错位、无缺卡 |
| 开考实测 | **81/81 返回 200**；空卷 0；首题题干为空 0；英语卷听力音频非 200 为 **0** |
| 题量 | 每级 9 张、合计 2088 题（单元 55 / 期中 85 / 期末 92 每级） |

### 9.3 本轮修掉的两个问题

**(a) 筛选器列出不存在的学科/类型**
首屏筛选条按 `Subject.values` 全枚举，出现物理/化学/生物/历史/地理/政治与「模考」，但库里只有语数英 × 单元/期中/期末，学生点下去必然空结果。改为首屏加载时记录「当前年级实际有卷的学科/类型」，筛选条只渲染这些；首屏无数据时退回全量兜底。测试同步收紧（无模考卷 → 「模考」`findsNothing`；无物理卷 → 「物理」`findsNothing`）。

**(b) 真题库入口承诺了不存在的内容**
首页「真题库」副标题常驻「按学科、年份与地区查看历年真题」，而真题库当前 0 张（自建题库口径，不接版权真题）。改为并行探一次（`pageSize=1`），为空时显示「当前年级暂未收录真题」，探测失败时保持原文案 —— 不因为探测失败就谎报「没有」。

### 9.4 关于上一节的听力额度遗留

第 8 节末尾记的「播放次数限制尚未做」已补齐：`POST /api/exams/attempts/{id}/listening-plays` 记账，每 attempt 上限 2 次，超限 429；音频接口带 `attempt_id` 时兜底记账并回 `X-Listening-Play-Remaining`。**练习/复习不传 `attempt_id`，不限次**。真机双向取证：练习页连点 4 次只产生 1 条服务端 GET（之后走本地缓存）；试卷口径同题连发 3 次 → 全 429。

### 9.5 走查侧的收尾

- 全量题目快照（2088 题，8 类机检 0 异常）与 81 份按卷 Markdown 已产出，教研可逐卷打开复核，不必再依赖真机截图。
- 本轮产生的 attempts 已清理，学生 `grade` 复原为 g1，历史作答记录未受影响。
