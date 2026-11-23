# 深圳初中教材版本核对与 7–9 年级英语内容整改

> 触发：用户指出「初中英语是上教版、政治是人教版」，质疑库内教研数据挂错版本。
> 执行日期：2026-11-22。数据库：本地 PostgreSQL `ailearning`（127.0.0.1:15432）。
> 执行前全库备份：`D:\AiLearning\backup\ailearning-<yyyyMMdd_HHmm>.dump`（1.59 MB，pg_dump -Fc）。

## 1. 版本核实结论

深圳初中教材版本以市教科院《2025—2026 学年义务教育免费教辅材料及教学资源选用目录》与市招考办说明为准：

| 学科 | 深圳实际版本 | 库内原标注 | 结论 |
| --- | --- | --- | --- |
| 英语 | 上教版（沪教牛津深圳版，上海教育出版社，深圳/广州/沈阳通用） | 牛津深圳版 | 出版社口径不全，需规范 |
| 道德与法治 | 人教版（统编，原「部编」表述即统编教材） | 部编版 | 版本名需与英语口径统一 |
| 语文 | 人教版 | 人教版 | 一致 |
| 数学 | 北师大版 | 北师大版 | 一致 |
| 历史 | 人教版（统编） | 部编版 | 未在本次范围，保持原样 |
| 地理 | 湘教版 | 湘教版 | 一致 |
| 物理 / 生物 / 化学 | 人教版 | 人教版 | 一致 |

核对来源：

- 深圳市教科院教辅目录（英语「配上教版」，道法「配人教版」）：<http://www.szjky.edu.cn/attachment/0/95/95450/1614133.pdf>
- 深圳市招考办说明：<https://szeb.sz.gov.cn/szzkw/qt/tzgg/content/post_12355970.html>
- 沪教牛津深圳版教材书目：<http://www.dzkbw.com/books/hjb/yingyu/oxford7s_2024/001.htm>、<http://www.dzkbw.com/books/hjb/yingyu/oxford8s_2025/012.htm>、<http://www.dzkbw.com/books/hjb/yingyu/8x_2026/>

## 2. 库内真实偏差（比版本名更严重）

核对后发现偏差不只是版本字符串，而是**内容与教材不同版**：

- 英语 7–9 原章节用的是「牛津**上海**版」目录（7A: Trying new things / Strong mind / Jobs / Smart home / Films / Mountains and rivers 等，每册 6 单元），
  与深圳实际使用的「沪教牛津**深圳**版」新教材（每册 8 单元）完全不同 → 章节、知识点、题库、试卷全部联动错位。
- 道法章节本就是人教版统编新教材目录（7 上「少年有梦 / 成长的时空 / 珍爱我们的生命 / 追求美好人生」、8 下「坚持宪法至上 / 理解权利义务 / 认识国家制度 / 走近国家机构 / 建设法治中国」、9 上「坚持党的全面领导 / 进入新时代 / 奋进新征程 / 共圆中国梦」），
  仅版本名字段口径需改，内容无需重建。

## 3. 整改动作

脚本：`backend/scripts/align_sz_curriculum.py`（版本口径 / 英语章节与知识点 / 题–知识点回挂 / 道法清理）、
`backend/scripts/seed_english_by_unit.py`（按单元铺题）、`backend/scripts/seed_english_writing.py`（书面表达）、
`backend/scripts/regen_english_papers.py`（重出期中期末卷）。

1. **版本改名**：英语 1–9 年级 18 册 → `上教版（沪教牛津深圳版）`；道法 1–12 年级 24 册 → `人教版（部编）`。
2. **英语 7–9 章节按上教版新教材目录重建**（每册 8 单元，7A 2024 秋 / 7B 2025 春 / 8A 2025 秋 / 8B 2026 春 / 9A 2026 秋）：
   - g7：16 单元，g8：16 单元，g9：8 单元；
   - 九年级下册官方目录未公布（预计 2027 春），以单条占位章节「待发布·上教版新教材九年级下册」处理，不铺题。
3. **知识点重建**：每单元 1 个 section + 4 个 point（听力与主题词汇 / 语法要点 / 语篇理解 / 词汇填空与表达），
   共 40 section + 160 point（g7 64、g8 64、g9 32）。
4. **题库重跑**：每单元 32 题（听力 8 / 语法单选 8 / 阅读 6 / 填空 10），7–9 共 1280 题；
   另补 20 道书面表达（每册 4 道，落 U1/U3/U5/U7，含评分要点与参考范文）。
   全部 1300 题按题型回挂到对应单元 point，无悬空知识点。
5. **试卷重建**：删除 9 张旧英语卷，按 `POST /api/exams/generate` 重出 9 张
   （单元卷 28 题 / 60 分，期中期末 39 题 / 100 分），期中与期末强制使用不同写作题。
6. **道法清理**：删除 14 个游离 section（`第一课丰富的社会生活`、`诚实守信` 及 12 个「样章·道德与法治·观点与材料」），
   并将「第一单元走进社会生活」规范为「第一单元 走进社会生活」。

## 4. 整改后验收

| 指标 | 整改前 | 整改后 |
| --- | --- | --- |
| 英语 7–9 章节 | 6 单元/册（牛津上海版目录） | 8 单元/册（上教版深圳版） |
| 英语 7–9 知识点 | 旧单元名联动错位 | 40 section + 160 point，1300 题全挂载 |
| 英语 7–9 题量 | 1468（旧版目录残留） | 1300（1280 单元题 + 20 写作） |
| 试卷总数 | 72（删旧英语卷后） | 81（恢复基线，含 9 张新英语卷） |
| 内容自检 | — | issue 0 / warning 0 / 覆盖缺口 0 / 分值不一致 0 |
| 试卷体检（audit_published_papers） | — | 81 卷 issues 0（仅 16 条 LEAK_INFO 信息级） |
| 音频资产 | 15778 个 / 505.8 MB | 16565 个 / 540.3 MB，听力题覆盖 1356/1356（100%） |
| 内容包 | `ailearning-content-20261119.json.gz`（含旧章节） | `ailearning-content-20261122.json.gz`（146 册 / 728 章 / 3425 KP / 18278 题 / 81 卷） |

补充说明：

- 音频重建需 ffmpeg，本机 ffmpeg 未在 PATH（位于 WinGet 包 `Gyan.FFmpeg...\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe`），
  需以 `FFMPEG_BIN` 指向后执行 `python -m scripts.build_question_audio --grade 7,8,9 --subject english --kind reading,listening`。
  本轮结果：生成 817、跳过 483、失败 0。
- 本地部署（含公网隧道）已恢复：`127.0.0.1:18080`，公网 `https://hit-heard-mailing-borough.trycloudflare.com`（quick tunnel，重启即变，状态见 `D:\AiLearning\run\local-deploy.json`）。

## 5. 未决事项

- **9 下（九年级下册）**：上教版新教材尚未发布，当前为占位章节、不铺题。需要过渡方案时再决策（用旧版目录过渡 or 等官方目录）。
- **小学英语 1–6**：版本名一并改为「上教版（沪教牛津深圳版）」（深圳小学英语同为沪教牛津，方向一致），但内容未逐册复核。
- **历史**：仍为「部编版」，未纳入本次整改，是否统一为「人教版（部编）」待定。

## 6. App 重装与真机验证（2026-11-23）

构建与安装（真机必须走 `127.0.0.1`，模拟器口径 `10.0.2.2` 在真机上不可达）：

```powershell
pwsh scripts\build-apk.ps1 -DebugBuild -ApiBaseUrl http://127.0.0.1:18080
# 运行前需把 C:\Windows\System32（where.exe）与 C:\Program Files\Git\cmd 加进 PATH
adb reverse tcp:18080 tcp:18080
adb install -r -d app\build\app\outputs\flutter-apk\app-debug.apk
```

- 构建：`flutter build apk --target-platform android-arm64 --debug --dart-define API_BASE_URL=http://127.0.0.1:18080`，90 s 成功，`app-debug.apk` 108.8 MB。
- 设备：HUAWEI EBG-AN00，SN `2NSDU20423005421`，Android 12，1080×2340 @480dpi。

走查结果：

| 环节 | 结果 |
| --- | --- |
| 安装 | `Success`（覆盖安装，保留数据） |
| 冷启动 | 登录 `13900000001` → 首启协议同意 → 三段引导（初中 / 7 年级 / 确认教材）→ 学习首页 |
| 教材下发 | 引导第 3 步「确认教材」显示「**英语 7 年级 · 上教版（沪教牛津深圳版）**」；同屏语文人教版、数学北师大版、生物人教版、历史部编版、地理湘教版 |
| 组卷 | 同步巩固·英语：15 题 / 预计 9 分钟 / 知识点覆盖 13/32（41%）/ 听力 6 + 单选 5 + 填空 4 |
| 听力音频 | 点「播放听力材料」→ `GET /api/learn/questions/23531/audio?speed=1.0&kind=listening` 200，AudioFlinger 实际出声，无 404、无 FATAL |
| 证据截图 | `docs/content-templates/exports/ebg_step3.png`、`ebg_english_scope.png`、`ebg_answer_q1.png`、`ebg_audio_play.png` |

观察项（不影响交付，建议后续优化）：

1. g7 听力首题选项为 `head / hand / eye / ear`，与 `Unit 1 Friendship` 主题贴合度不足，建议按单元主题词表重写干扰项。
2. 学科选择弹窗底部出现 Flutter `BOTTOM OVERFLOWED BY 157 PIXELS`，需调整弹窗高度/滚动。
3. 验证期间为看 g7 内容曾把质检学生 `grade` 临时改为 7，走查后已改回 1。

## 7. 整改后修复（2026-11-23 第二轮，已全部实施）

上一节三条观察项已按「修复回来 / 修改掉 / 按建议处理」全部收口，不再作为待优化挂账。

### 7.1 走查痕迹复原

| 项 | 走查后残留 | 处置 | 复原结果 |
| --- | --- | --- | --- |
| 学生画像 | `grade=8 / stage=junior`（7 年级走查后又落到 8 年级） | 改回 `grade=1 / stage=primary` | `/api/learn/home` 返回 `grade=1` |
| 教材绑定 | 7 条 `active` 绑定全部指向 7 年级（生物/语文/英语/地理/历史/数学/政治） | 全量置 `archived` → `textbook_service.auto_bind()` 按 1 年级重绑 | 3 科：语文（id 3）/ 数学（id 1）/ 英语（id 5） |
| home 缓存 | 进程内 `home:{user}:{grade}:{semester}` 缓存仍返回旧教材 | 重启 uvicorn | 缓存重建后即返回 1 年级 |
| App 本地态 | 协议同意、登录态、离线缓存 | `adb shell pm clear` + 重走首启 | 首页「小学 · 1 年级 · 上学期」 |

### 7.2 听力题按单元主题化

根因：`backend/scripts/english_by_unit_data.py` 的 `listening_item(idx)` 用「12 个通用词群 × 全局游标」解码，40 个单元共享同一批词，且 `answer` 硬编码 `A`。

修复：新增 `UNIT_LISTENING_WORDS`（40 单元 × 8 主题词）与 `listening_items_for_unit()`（干扰项限同单元词表、答案位置按题序 A/B/C/D 轮转）；`seed_english_by_unit.build_for_chapter()` 增加 `chapter_name` 入参，7-9 走主题化、1-6 回退旧词池。

| 验收项 | 结果 |
| --- | --- |
| 重跑改写 | 1280 题（含 320 道 g7-9 听力） |
| 答案分布 | A / B / C / D 各 80 |
| 抽样 | 7A Unit 1 Friendship → friend·friendly·kind·helpful…；8A Unit 1 Look it up! → dictionary·entry·word·meaning…；9A Unit 1 Great people → hero·great·courage·leader… |
| KP 回挂 | 7-9 英语 1300 题未挂知识点 = 0 |
| 音频重生成 | `--kind listening --grade 7,8,9 --subject english --force` → 生成 320 / 跳过 0 / 失败 0 |
| 全库自检 | `content_selfcheck` issue 0 / warning 0；`audit_published_papers` 81 卷 issues 0（16 条 LEAK_INFO） |

### 7.3 学科选择弹窗溢出

`app/lib/features/learn/learn_page.dart#_openPracticeMode`：`showModalBottomSheet` 增 `isScrollControlled: true`，内容套 `ConstrainedBox(maxHeight: 屏高 0.7)`，列表改 `Flexible(ListView(shrinkWrap: true))`。`flutter analyze` 0 issue，EBG-AN00 复验黄黑条消失、末项完整、可滚动。

### 7.4 版本口径与定时任务

| 项 | 结果 |
| --- | --- |
| 历史学科 | 12 册 `部编版` → `人教版（部编）` |
| 英语 / 道法 / 历史 每日教研任务 | query 内 `version=` 与 `--expect-version` 全部换新口径（任务仍暂停，未擅自启用） |
| 远端 | 本轮改动已 commit 并 push `origin/main` |


