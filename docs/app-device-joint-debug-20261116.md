# App 重构与真机联调报告（2026-11-16 晚）

> 设备：EBG-AN00（华为，Android 12 / API 31），adb 序列号 `2NSDU20423005421`
> Flutter：3.41.10-ohos-1.0.1（Dart 3.11.5）；JDK 17（`MyLangLean\.tools\jdk17\jdk-17.0.2`）
> 后端：本机 uvicorn `0.0.0.0:18080`，真机经 `adb reverse tcp:18080 tcp:18080` 直连
> 账号：内容管理员 / 超级管理员（13800000000）

---

## 一、本轮重构内容

| # | 改动 | 文件 |
|---|---|---|
| 1 | 新增纯文本 GET 能力（用于取 HTML 答题卡） | `app/lib/core/services/api_client.dart`（`getText`） |
| 2 | 新增试卷文档服务方法：`specTable()` / `answerSheetHtml()` | `app/lib/core/services/exam_service.dart` |
| 3 | 新增细目表行模型 `ExamSpecRow`（含 `matches` 计划=实际判定） | `app/lib/core/models/exam.dart` |
| 4 | 组卷结果卡后新增「双向细目表」「答题卡」两个入口与两个弹窗 | `app/lib/features/exam/exam_manage_page.dart` |
| 5 | 修复真机暴露的蓝图下拉横向溢出（163px）：`isExpanded` + `ellipsis` + `selectedItemBuilder` | 同上 |

设计取向：组卷页原本只能「生成即完事」，教师拿到卷看不到卷结构、也拿不到打印用答题卡。两个入口把 PG-05 已有的后端能力（`/api/exams/{id}/spec-table`、`/api/exams/{id}/answer-sheet`）接到端上，不新增后端接口。

---

## 二、质量门禁

| 检查 | 结果 |
|---|---|
| `flutter analyze` | No issues found（4.5s） |
| `flutter test` | **175 passed** |
| `flutter build apk --debug` | 成功，产物 `app/build/app/outputs/flutter-apk/app-debug.apk`（约 150 MB） |
| 安装到真机 | `flutter install -d 2NSDU20423005421` 成功 |
| 后端 `pytest` | 462 passed（本轮未改后端逻辑） |

---

## 三、真机走查（逐屏截图）

| 步骤 | 预期 | 实测 | 截图 |
|---|---|---|---|
| 冷启动 | 首启隐私同意页，未勾选时按钮禁用 | 通过 | `shots/device_launch.png` |
| 勾选同意 | 按钮变为可用、可进入 | 通过 | `shots/device_consent.png` |
| 登录页 | 手机号/密码可输入，错误提示为服务端原文 | 通过（错误时提示「手机号或密码错误」） | `shots/s8.png` |
| 管理员登录 | 进入「学习」页，显示「你好，内容管理员」 | 通过 | `shots/s9.png` |
| 我的页 | 显示超级管理员身份与各中心入口 | 通过 | `shots/m1.png` |
| 考试管理与发布 | 蓝图列表加载（81 条） | 通过，**但下拉文字溢出 163px** | `shots/g1.png` |
| 生成试卷 | 选蓝图 + 章节 ID → 生成即发布 | 通过：`ID 7 · 15 题 · 60 分 · KP 覆盖 100% · 兜底 0 · 已发布` | `shots/r3.png` |
| 双向细目表 | 逐节显示计划 vs 实际，一致打绿勾 | 通过：4 节全部「计划=实际」 | `shots/d1.png` |
| 答题卡 | 返回 HTML，含题号与作答区、不含题干与答案 | 通过：约 3382 字符，未含题干 | `shots/d4.png` |

### 第二轮（答题卡改版后重装复验，2026-11-16 12:26–12:30）

| 步骤 | 实测 | 截图 |
|---|---|---|
| 重装后冷启动→同意页→管理员登录 | 通过（`adb shell` 输入 13800000000/admin123） | `shots/v1.png`~`v3.png` |
| 组卷页 | 蓝图下拉已省略号截断，无 overflow 红条 | `shots/v4.png`、`v7.png` |
| 生成试卷（g1 语文期末，章节 153–160） | **通过**：`ID 8 · 18 题 · 100 分 · KP 覆盖 53% · 兜底 0 · 已发布` | `shots/w2.png` |
| 答题卡弹窗（改版后） | **通过**：摘要「3653 字符，不含题干与答案」+ 前 6 行 HTML 预览 + 「复制 HTML」「关闭」 | `shots/w4.png` |
| 点「复制 HTML」 | **通过**：SnackBar「答题卡 HTML 已复制到剪贴板」 | `shots/w5.png` |
| 章节 ID 只填 153（单章） | **被拒 422 `题量/难度不足`**（fill 需 8 条，单章仅 3 条）→ 印证手填章节 ID 是真实可用性缺陷 | — |

服务端调用链（uvicorn 日志）与上述操作一一对应：`POST /api/exams/generate 200` → `GET /api/exams/8/spec-table 200` → `GET /api/exams/8/answer-sheet 200`。

服务端调用链（uvicorn 日志）与上述操作一一对应：`POST /api/exams/generate 200` → `GET /api/exams/7/spec-table 200` → `GET /api/exams/7/answer-sheet 200`。

---

## 四、真机暴露的问题与处置

| # | 问题 | 处置 |
|---|---|---|
| 1 | 蓝图下拉文字横向溢出（`RIGHT OVERFLOWED BY 163 PIXELS`），长蓝图名被裁切 | 已修：`isExpanded: true` + `TextOverflow.ellipsis` + `selectedItemBuilder` |
| 2 | 答题卡弹窗直接铺 HTML 源码，教师无法落地使用 | 已改为「摘要 + 前 6 行预览 + 复制 HTML 到剪贴板」 |
| 3 | 组卷必须手填章节 ID（例如 `153,154`），易错 | **未修**。实测把「1年级语文单元测试卷」只填单章 `153` 会直接得到 422 `题量/难度不足`（该卷型需要 8 条 fill，单章仅 3 条），用户无法从界面得知「单元卷必须填构成该单元的 2 个章节」。建议改为按教材→单元的多选器（P1） |
| 4 | 管理员进入「错题本」时 `GET /api/learn/wrong-questions?status=active` 返回 422 `STUDENT_ID_REQUIRED` | **未修**，属既有行为：该接口按学生维度取数，管理员需先选学生。建议端上在非学生角色时改为「选择学生」引导，而不是直接报错 |
| 5 | 键盘弹出时华为系统屏蔽截屏（`screencap` 返回 0 字节） | 非缺陷，走查时先 `keyevent 4` 收键盘再截图 |

---

## 五、未覆盖的走查链路（如实记录）

- 学生端作答 → 交卷 → 报告 → 主观题自评，未在本轮真机跑通（需要学生账号与新卷派发）。
- 班级派发（`派发到班级`）、教师中心、家长中心、内容审核双人流程未逐一走查。
- 离线答题与同步（`offline_exam_store/sync`）未验证。
- Release 包未构建（本轮为 debug，且 `--dart-define` 指向 `127.0.0.1:18080` 仅用于 USB 联调）。

---

## 六、复现命令

```powershell
# 1) 后端
cd D:\ai\prj\trae\HuaWei\AiLearning\backend
$env:PYTHONPATH='D:\ai\prj\trae\HuaWei\AiLearning\backend'
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 18080

# 2) 真机端口反向映射
D:\ai\prj\trae\HuaWei\MyLangLean\.tools\android-sdk\platform-tools\adb.exe `
  -s 2NSDU20423005421 reverse tcp:18080 tcp:18080

# 3) 构建 + 安装
cd ..\app
$env:JAVA_HOME='D:\ai\prj\trae\HuaWei\MyLangLean\.tools\jdk17\jdk-17.0.2'
flutter build apk --debug --dart-define=API_BASE_URL=http://127.0.0.1:18080
flutter install -d 2NSDU20423005421 --debug
```

截图目录：`docs/content-templates/shots/`
