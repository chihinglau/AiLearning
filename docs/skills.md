# 深爱学（AiLearning）本地开发 Skill 手册

> 项目：深圳中小学（小学 / 初中 / 高中）跨平台学习辅助应用
> 技术栈：Flutter（Android + HarmonyOS NEXT）+ FastAPI / SQLAlchemy / PostgreSQL
> 当前阶段：M1 技术底座（账号、教材章节、同步练习闭环已跑通）
> 本手册只记录**本项目实际可用**的命令与坑，环境策略与 RetroEmuPouch 一致：零安装、全复用、省磁盘。

---

## 0. 一句话总览

```powershell
# 每个新终端先注入环境（Android + 鸿蒙）
. .\scripts\use-env.ps1 -Ohos

# 后端
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 18080

# 客户端（另开终端，同样先点源 use-env）
cd app
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:18080
```

---

## 1. 仓库结构速记

```
AiLearning/
├─ backend/                 FastAPI 后端
│  ├─ app/main.py           应用入口 / CORS / 路由注册
│  ├─ app/core/             配置、JWT、bcrypt、业务常量
│  ├─ app/models/           users / textbooks / chapters / questions / records / exams …
│  ├─ app/api/routes/       auth / public / practice / admin / health
│  ├─ app/schemas/          Pydantic v2 出入参
│  ├─ alembic/              迁移（首个版本已建全部表）
│  ├─ scripts/seed.py       管理员 + 体验学生 + 小学示例内容
│  └─ tests/                pytest（SQLite + StaticPool）
├─ app/                     Flutter 客户端
│  ├─ lib/core/             constants / models / services / providers
│  ├─ lib/pal/              PlatformPal 抽象 + android / ohos 实现
│  ├─ lib/features/         auth / home / practice
│  ├─ android/              Android 工程
│  └─ ohos/                 HarmonyOS 工程（bundleName: com.ailearning.ai_learning）
├─ docs/                    设计文档（k12-learning-app-design.md）与本手册
├─ scripts/                 环境脚本（setup-env / use-env / setup-backend）
└─ .tools/                  全部为 junction，指向共享工具链（不占额外空间）
```

---

## 2. 环境初始化（零安装，复用共享工具链）

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup-env.ps1
```

脚本做的事（幂等，可重复执行）：

| `.tools/` 名称 | 指向 | 用途 |
|---|---|---|
| `flutter` | `MyLangLean\.tools\flutter` | Android / 通用 Flutter（3.47.x stable） |
| `flutter_ohos` | `MyLangLean\.tools\flutter_ohos` | 鸿蒙 Flutter fork（3.41.10 / Dart 3.11.5） |
| `android-sdk` | `MyLangLean\.tools\android-sdk` | Android SDK 36 + platform-tools |
| `jdk17` | `MyLangLean\.tools\jdk17` | 备用 JDK |
| `jdk21` | `RetroEmuPouch\.tools\jdk21` | 默认 JDK（Gradle / Kotlin DSL 更稳） |
| `caches` | `MyLangLean\.tools\caches` | pub-cache、Gradle 缓存共享，避免重复下载 |

要点：

- **不要再单独安装 JDK / Android SDK / Flutter / DevEco**。node、ohpm、hvigor 直接用 DevEco Studio 自带（`D:\HuaWei\DevEco-Studio\tools`）。
- junction 本身不占磁盘；依赖包只进共享 `caches`，不按项目复制。
- `jdk21` 是 junction，指向同级 RetroEmuPouch 项目；若该项目被移动/删除，重跑脚本会回退到 `jdk17`（Gradle 8.x 可用）。
- 脚本会同步 `app/ohos/local.properties` 的 `flutter.sdk`，避免指向其他仓库。

---

## 3. 会话环境注入（每个新终端必做）

```powershell
. .\scripts\use-env.ps1              # Android：JAVA_HOME / ANDROID_HOME / flutter stable
. .\scripts\use-env.ps1 -Ohos         # 鸿蒙：flutter_ohos + node/ohpm/hvigor + OpenHarmony SDK
. .\scripts\use-env.ps1 -Ohos -HarmonyOS   # 上架版：切 DevEco HarmonyOS 26 SDK（含 hms）
```

- 必须 **dot-source（`. `）**，不要直接运行脚本，否则环境变量不会留在当前会话。
- 注入内容：`AIL_ROOT`、`JAVA_HOME`、`ANDROID_HOME`、`PUB_CACHE`、`GRADLE_USER_HOME`、镜像地址（`PUB_HOSTED_URL` / `FLUTTER_STORAGE_BASE_URL`）。
- `-Ohos` 额外注入 `OHOS_SDK_HOME` / `OHOS_BASE_SDK_HOME` / `DEVECO_SDK_HOME` / `HOS_SDK_HOME`，并把 `hdc`（`D:\HuaWei\OhosSdkForFlutter\26\toolchains`）加入 PATH。

验证：

```powershell
node --version          # v24.x
ohpm --version          # 26.x
hvigorw --version       # 6.x
java -version           # 21.0.x
flutter doctor          # HarmonyOS toolchain 应为 [√]
```

---

## 4. 后端开发

### 4.1 初始化 / 依赖

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup-backend.ps1
```

等价手动步骤：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m scripts.seed
```

- 当前 venv 基于 **Python 3.10.11**，代码按 3.10 兼容写法；升级 3.12 前先跑全量 pytest。
- 默认数据库 `sqlite:///./ailearning_dev.db`（开箱即用）；生产切 PostgreSQL：
  `DATABASE_URL=postgresql+psycopg://user:pass@127.0.0.1:5432/ailearning`。
- JSON 字段统一用 `app/db/types.py` 的 `JSONType`（PG 用 JSONB，SQLite 自动降级为 JSON）。

### 4.2 启动与文档

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 18080
```

- Swagger：<http://127.0.0.1:18080/docs>　健康检查：`/health`
- 种子账号：管理员 `131808000000 / admin123`，体验学生 `13900000000 / student123`
- 学生端登录用 OAuth2 表单（`username=手机号`），不是 JSON。

### 4.3 API 清单

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| POST | `/api/auth/register` | 注册（仅 student / parent，管理员只能由种子脚本创建） |
| POST | `/api/auth/login` | 表单登录，返回 JWT |
| GET | `/api/auth/me` | 当前账号 |
| GET | `/api/public/textbooks` | 教材（`subject` / `grade` 过滤） |
| GET | `/api/public/chapters` | 章节（`textbook_id`） |
| GET | `/api/public/knowledge-points` | 知识点 |
| POST | `/api/practice/start` | 抽题（chapter_id / knowledge_point_id / subject + count） |
| POST | `/api/practice/submit` | 提交答案并判题（返回正确答案与解析） |
| GET | `/api/practice/history` | 答题记录 |
| GET/POST | `/api/admin/textbooks` | 教材管理（需 admin） |
| POST | `/api/admin/chapters` | 章节管理（需 admin） |
| GET/POST | `/api/admin/questions` | 题库管理（需 admin，含答案） |

学生端抽题接口**不返回** `answer` / `analysis`，避免客户端作弊。

### 4.4 测试

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

- 覆盖：健康检查 / OpenAPI、注册登录鉴权、管理员越权拦截、抽题-判题-历史闭环。
- 测试用内存 SQLite（`StaticPool`）+ 依赖覆盖，不触碰开发库。

---

## 5. 客户端开发

### 5.1 依赖与静态检查

```powershell
. .\scripts\use-env.ps1 -Ohos    # 有 ohos 目录时必须带 -Ohos，否则 flutter CLI 会因缺 npm 崩溃
cd app
flutter pub get
flutter analyze
flutter test
```

### 5.2 本地运行

```powershell
# Android 模拟器访问宿主机
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:18080

# 真机（USB 调试，先 adb devices 确认）
flutter run --dart-define=API_BASE_URL=http://<PC局域网IP>:18080
```

- 默认 `API_BASE_URL=http://127.0.0.1:18080`（见 `lib/core/constants/app_constants.dart`）。
- 已实现闭环：登录 → 教材 / 章节 → 答题 → 判题反馈 → 结算。
- 登录页默认填充体验学生账号（需先执行 `scripts.seed`）。

### 5.3 打包 Android APK

统一走脚本（内置共享工具链，自动 `pub get`、超时保护、`gradlew --stop` 清守护进程）：

```powershell
# 默认 release、单 ABI (arm64)
powershell -ExecutionPolicy Bypass -File scripts\build-apk.ps1

# 调试包
powershell -ExecutionPolicy Bypass -File scripts\build-apk.ps1 -DebugBuild

# 按 ABI 拆包 / 打 AAB（应用商店）
powershell -ExecutionPolicy Bypass -File scripts\build-apk.ps1 -SplitPerAbi
powershell -ExecutionPolicy Bypass -File scripts\build-apk.ps1 -BuildAab
```

参数：`-DebugBuild`、`-SplitPerAbi`、`-BuildAab`、`-NoPubGet`、`-ApiBaseUrl`。
产物：`app\build\app\outputs\flutter-apk\`（APK）或 `bundle\release\`（AAB）；完整日志 `build-apk.log`。

**Release 签名**（首次）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\make-release-keystore.ps1
```

生成 `.tools\signing\ailearning.jks` 与 `keystore.properties`（均 gitignore），并在 `.tools\signing\backup\` 自动归档一份带时间戳的 zip。重复执行时复用 `keystore.properties` 中已记录的密码，不会覆盖已有 keystore。

- **禁止 debug 回退**：`app/android/app/build.gradle.kts` 在 release 构建时若缺 `keystore.properties` / 签名文件不存在，直接抛出 Gradle 异常并中止；debug 构建不受影响。
- **签名指纹归档**：`scripts\signature-info.ps1` 导出证书 MD5/SHA-256 并校验 APK 实际签名（要求 `CN=AiLearning`），输出 `build\signatures\signature-<时间戳>.txt`，用于 APP 备案。
- 首次打包若提示 license：`flutter doctor --android-licenses`（一次性）。
- 上架前请用密钥管理系统/HSM 生成正式签名并加入应用商店的应用签名计划；keystore 丢失将无法升级。
- 包名 `com.ailearning.ai_learning` 与签名证书一经备案**终身不变**。

**发版号规则**（Android 与 HarmonyOS 必须同值）：

```
versionCode = major * 10000 + minor * 100 + patch * 10 + build
例：pubspec version: 1.0.0+1 -> versionCode 10001
```

`app/pubspec.yaml` 是唯一版本来源。Android 由 `build.gradle.kts` 构建期按同一公式计算；HarmonyOS 用脚本写入 `app/ohos/AppScope/app.json5`：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\sync-version.ps1          # 写入并打印
powershell -ExecutionPolicy Bypass -File scripts\sync-version.ps1 -Check   # 只校验双端一致
```


### 5.4 打包鸿蒙 HAP

#### 5.4.1 构建前必须对齐的配置（否则 hvigor 报 SDK 不匹配 / 非鸿蒙类型）

| 文件 | 字段 | 取值 |
|---|---|---|
| `app/ohos/build-profile.json5` | `compatibleSdkVersion` | `"26.0.0"` |
| `app/ohos/build-profile.json5` | `runtimeOS` | `"HarmonyOS"`（不是 `"OpenHarmony"`） |
| `app/ohos/build-profile.json5` | `signingConfigs` | 默认空，由 DevEco 自动签名或 `sign-ohos-hap.ps1` 注入 |
| `app/ohos/oh-package.json5` | `modelVersion` | `"6.0.0"` |
| `app/ohos/entry/src/main/module.json5` | `deviceTypes` | `["default"]` |
| `app/ohos/AppScope/app.json5` | `bundleName` | `com.ailearning.ai_learning` |
| `app/ohos/local.properties` | `flutter.sdk` | 本仓库 `.tools\flutter_ohos`（由 `setup-env.ps1` 写入） |

> 上述值已由本仓库脚手架修正；如被 `flutter create` 覆盖，重跑 `scripts\setup-env.ps1` 并核对。

#### 5.4.2 构建

```powershell
# debug 自动签名
.\scripts\build-hap.ps1
# release
.\scripts\build-hap.ps1 -Release
# 只编译不签名（验证编译是否通过）
.\scripts\build-hap.ps1 -NoCodesign
```

`build-hap.ps1` 会点源 `use-env.ps1 -Ohos -HarmonyOS`（切 HarmonyOS 26 SDK，含 hms）。
产物：`app\build\ohos\hap\entry-default-signed.hap`（自动签名）或 `entry-default-unsigned.hap`。

#### 5.4.3 本地 debug 签名（不想开 DevEco 时）

```powershell
.\scripts\sign-ohos-hap.ps1
```

该脚本用 OpenHarmony SDK 的 `hap-sign-tool.jar` 自签 CA + app 叶证书 + profile，
并把真机 UDID 写入 profile 的 `device-ids`，最后签名 HAP。
需先 `hdc list targets` 确认设备已连接（否则 UDID 为空）。

#### 5.4.4 安装 / 抓日志

```powershell
hdc list targets
hdc install -r app\build\ohos\hap\entry-default-signed.hap
hdc hilog | Select-String -Pattern "AiLearning|OhosPal"
```

- `flutter pub get` 在 `-Ohos`（OpenHarmony）模式提示 `No Hmos SDK found` 属正常；构建 HAP 统一用 `-HarmonyOS`。
- 真机 `hdc` 在 `use-env.ps1 -Ohos` 已加入 PATH（`D:\HuaWei\OhosSdkForFlutter\26\toolchains`）。

### 5.5 真机联调（Android + 鸿蒙）

#### 5.5.1 Android 真机（adb）

**连接**

```powershell
adb devices -l                        # 应看到 EBG-AN00（EBG）或局域网 IP
adb tcpip 5555                        # 有线转无线（需同 Wi-Fi）
adb connect 192.168.1.8:5555          # 设备 IP 用 adb shell ip addr show wlan0 查看
```

**安装 / 卸载**

```powershell
adb install -r app\build\app\outputs\flutter-apk\app-debug.apk
adb uninstall com.ailearning.ai_learning
```

**启动 / 日志 / 截图**

```powershell
adb shell am start -n com.ailearning.ai_learning/.MainActivity
adb logcat -d -t 100 | Select-String -Pattern "AiLearning|flutter|ai_learning|FATAL"
adb exec-out screencap -p > screen.png
```

**注意**
- 真机访问后端请改用 `http://<PC局域网IP>:18080`（不要再用 `10.0.2.2`）。
- 手机与 PC 需同 Wi-Fi，且 Windows 防火墙允许 18080 入站。

#### 5.5.2 鸿蒙真机（hdc）

**连接**

```powershell
hdc list targets                      # 看到 SN（如 2MN0224730027764）即连上
hdc tconn 192.168.x.x:5555            # 无线调试
hdc -t <SN> <cmd>                     # 多设备时指定 SN
```

**安装 / 卸载 / 启动**

```powershell
hdc install -r app\build\ohos\hap\entry-default-signed.hap
hdc uninstall com.ailearning.ai_learning
hdc shell aa start -a EntryAbility -b com.ailearning.ai_learning
```

**抓日志 / 截图 / UI**

```powershell
hdc shell hilog | Select-String -Pattern "AiLearning|OhosPal"
hdc shell snapshot_display -f /data/local/tmp/x.jpeg
hdc file recv /data/local/tmp/x.jpeg .\x.jpeg
hdc shell "uitest uiInput click x y"
```

#### 5.5.3 真机锁屏与自签信任坑

- **鸿蒙 HAP 安装失败（no signature / verify pkcs7）**：自签 CA 不被设备信任。真机调试优先用 DevEco 自动签名（Project Structure → Signing Configs），它会装受信任的调试 CA；纯 CLI 自签仅用于编译验证。
- **锁屏后 `aa start` 报 `10106102`**：开发者模式 + 密码锁的设备必须先手动解锁。Pura70 建议：设置 → 关闭锁屏密码；开发者选项 → 充电时保持唤醒。USB 连接期间屏幕常亮，全程零解锁。
- **EBG-AN00（HWEBG）**：当前识别为 Android 设备（`adb`），非 HarmonyOS NEXT；如需鸿蒙联调请换用 Pura70（SN 2MN0224730027764）。

#### 5.5.4 本次 EBG 真机调试结果

- APK 已安装：`adb install -r app-debug.apk` → `Success`
- 包名验证：`com.ailearning.ai_learning`
- 已启动：`am start` 成功，无 FATAL / AndroidRuntime 异常
- 设备 IP：`192.168.1.8`（与 PC 同 Wi-Fi，ping 通）

> 截图文件 `ailaunch.png` / `ailaunch2.png` 拉取为 0 字节，疑为 EBG 机型兼容性问题；建议真机亮屏后再次 `adb exec-out screencap -p` 或用系统截图验证 UI。

---

## 6. 双端架构约定（PlatformPal）

```
features (UI)
   ↓ Riverpod providers
core/services (ApiClient / AuthService / ContentService)
   ↓
pal/platform_pal.dart  PlatformPal{ storage, account, screenTime }
   ├─ implementations/android/  AndroidStoragePal  (flutter_secure_storage / Keystore)
   ├─ implementations/ohos/     OhosStoragePal     (Hive 沙盒，待安全存储插件)
   └─ screen_time_pal.dart      CurfewScreenTimePal（22:00-06:00 强制休息）
```

新增平台能力（如推送、AI 语音、支付、时长统计）的固定步骤：

1. 在 `lib/pal/` 定义抽象接口（只暴露业务语义，不暴露平台 API）。
2. 在 `android/`、`ohos/` 各写一份实现；鸿蒙实现通过 ArkTS Platform Channel 对接。
3. 在 `PlatformPal` 聚合，`createPlatformPal()` 按 `Platform.isAndroid` / `Platform.operatingSystem == 'ohos'` 分流。
4. UI 层只依赖抽象；`flutter analyze` 必须零告警。

合规红线（客户端必须守住）：儿童账号家长绑定同意、每日时长限额（默认 120 分钟）、22:00-06:00 强制休息、消费二次验证。

---

## 7. 质量门（每次提交前）

```powershell
# 后端
cd backend; .\.venv\Scripts\python.exe -m pytest

# 客户端
. ..\scripts\use-env.ps1 -Ohos
cd ..\app; flutter analyze; flutter test
```

接口冒烟：

```powershell
Invoke-RestMethod http://127.0.0.1:18080/health
Invoke-RestMethod http://127.0.0.1:18080/api/public/textbooks
Invoke-RestMethod http://127.0.0.1:18080/openapi.json
```

---

## 8. 常见问题速查

| 现象 | 原因 / 解决 |
|---|---|
| `flutter` 报 `Failed to find "npm"` 崩溃 | 未点源 `use-env.ps1 -Ohos`，PATH 缺 DevEco node。点源后重试。 |
| `flutter doctor` 鸿蒙工具链 ✗ | 检查 node / ohpm / hvigorw 是否在 PATH（`use-env` 已加），以及 SDK 目录是否存在。 |
| `No Hmos SDK found`（pub get） | `-Ohos` 默认走 OpenHarmony SDK，正常；上架构建用 `-HarmonyOS`。 |
| Android 首次构建卡 license | `flutter doctor --android-licenses`，全部 `y`。 |
| `local.properties` 的 `flutter.sdk` 指向别的项目 | 重跑 `scripts\setup-env.ps1`；或手工改为 `...\.tools\flutter_ohos`（双反斜杠转义）。 |
| 数据库表不存在 | `alembic upgrade head`；开发库可删 `ailearning_dev.db` 重建后重新 seed。 |
| 登录 401 | 登录用 form 参数（`username/password`）；`/api/auth/me` 需 `Authorization: Bearer <token>`。 |
| 管理接口 403 | 注册接口不允许创建 admin；用 `scripts.seed` 的管理员账号。 |
| 中文在 PowerShell 里乱码 | 控制台编码问题，数据本身正确；需要时 `chcp 65001`。 |
| 端口 18080 被占用 | `Get-NetTCPConnection -LocalPort 18080` 找到 PID，或换 `--port 8001` 并同步 `API_BASE_URL`。 |
| 依赖体积变大 | 检查是否误用了默认 `%LOCALAPPDATA%\Pub\Cache`；`use-env` 的 `PUB_CACHE` 指向共享 `caches`。 |

---

## 9. 里程碑与已知缺口

- ✅ M1：FastAPI 骨架 + Alembic 首迁移 + 账号 / 公开内容 / 练习 / 管理 API；Flutter 双端骨架 + 登录-练习闭环；环境脚本与质量门；Android APK 与鸿蒙 HAP 构建脚本与签名方案已就位（见 5.3 / 5.4）。
- ⏳ 鸿蒙 HAP：真机安装验证（`hdc install`）。
- ⏳ M2：题库批量导入、错题本与复训调度、家长绑定与家长端、会员权益服务端校验。
- ⏳ 鸿蒙 Pal 实机能力：华为账号、Push、系统使用时长统计。

设计依据：[k12-learning-app-design.md](./k12-learning-app-design.md)
