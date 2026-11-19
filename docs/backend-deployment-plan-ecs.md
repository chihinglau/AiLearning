# 深爱学（AiLearning）后端部署方案：本地验证 → 独立 ECS

> **文档性质**：后端生产部署实施方案（与 `release-plan.md` 缺口 2/3/4 配套）
> **目标形态**：**独立阿里云 ECS**（不再与 RetroEmuPouch 共用）
> **当前阶段**：阶段 0「本地部署 + Cloudflare Tunnel」——**已实测通过（2026-11-19）**
> **目标域名**：`ailearnning.cn`（见 §4.7 拼写核验）
> **最后更新**：2026-11-19
> **关联文档**：`docs/release-plan.md`、`docs/project-task-plan.md`（R-02/R-03/R-06）、`docs/k12-learning-app-design.md`

---

## 0. 相对上一版（2026-11-17）的变更

| 变更 | 内容 |
|---|---|
| 部署形态 | ~~与 RetroEmuPouch 同机共用~~ → **独立 ECS**，本方案自建 Caddy，同 compose 内反代 |
| 作废章节 | 原 §2.2「复用 RetroEmuPouch 部署资产」、§3 跨栈架构、§3.1 loopback 端口矩阵、§5「Caddy 同机共存」（C7/C8）、§8 P2 中与 RetroEmuPouch 协同的 4 个步骤、§10 回滚中的 Caddy 恢复 |
| 作废原因 | 原方案核心技术路径 **实测证伪**：仅绑 `127.0.0.1` 的服务从容器侧不可达（详见附录 A-2） |
| 新增 | 阶段 0「本地部署 + Cloudflare Tunnel」全流程与实测数据（§3）；独立 ECS 规格测算与 D1–D10（§4）；三个 P0 交付缺口（§5）；A11–A15 验收（§6） |

---

## 1. 结论速览

| 维度 | 结论 |
|---|---|
| 阶段 0（本地 + Cloudflare） | **已跑通**：公网 HTTPS 下 `/health` 200、登录取 token、试卷列表（含 `x-total-count`）、听力/读题音频 200 + `audio/ogg` + ETag `304` 全部通过 |
| 阶段 1（独立 ECS） | **可行**：单栈内存估 150–300 MB、磁盘 <11 GB、2C2G 够用、2C4G 更稳；原共用方案唯一硬阻断项（跨栈 loopback）在本方案中天然消失 |
| 公网入口 | 阶段 0：Cloudflare quick tunnel（临时域名，零配置）；阶段 1：ECS 自建 Caddy 独占 80/443 + 自动 ACME |
| 数据库 | 独立 `postgres:16-alpine` + 独立 volume；阶段 0 无 Docker 时回退 SQLite dev 库 |
| 网络隔离 | API 只绑 `127.0.0.1:18080`，DB 不映射宿主端口；阶段 1 API 完全不发布宿主端口 |
| 阻断上线的 P0 | 原有 3 个：① 生产内容初始化（**已解决**：导出/导入数据包已实现并本地验证 18746 题 / 81 卷 / 1348 听力一致）；② 音频交付（**体积已实测 505.8 MB**、清单与校验工具就绪，仅剩实际传输与最终选型）；③ ICP 备案与解析切换（未解决，属时间阻断） |
| 工作量 | 阶段 0 已完成；阶段 1 约 **5.25–6.25 人日**（不含备案等待），其中 P0-A 已于 2026-11-19 提前完成 |

---

## 2. 两阶段路线

```
阶段 0（本周，验证链路与内容）          阶段 1（验证通过后，正式对外）
本机 Windows                           独立阿里云 ECS（Ubuntu 24.04）
  uvicorn/Docker ── 127.0.0.1:18080        caddy(80/443) ── api:8000 ── db
        │                                        │
  cloudflared quick tunnel                DNS → 独立公网 IP
        │                                        │
  https://xxx.trycloudflare.com           https://api.ailearnning.cn
        │                                        │
  真机 App（环境诊断改地址）              正式 APK/HAP（dart-define 注入）
```

阶段 0 的目的不是"临时凑合上线"，而是用**真实后端 + 真实内容 + 真机**把下列风险前移：鉴权、组卷、音频、ETag、中文编码、时延体感。阶段 1 只换承载与入口。

---

## 3. 阶段 0：本地部署 + Cloudflare Tunnel（已实测）

### 3.1 交付物

| 文件 | 作用 |
|---|---|
| `deploy/docker-compose.local.yml` | 本地栈：db + api（去掉 nginx），api 绑 loopback，音频只读挂载 |
| `deploy/.env.local.example` | 本地 env 模板（PG 口令、JWT、CORS、RUN_SEED） |
| `scripts/local-deploy.ps1` | 一键启停/状态：Docker 优先、uvicorn 兜底；起隧道并解析公网地址；公网自检 |

### 3.2 一键命令

```powershell
# 启动（自动选择 Docker 或 uvicorn，自动起 Cloudflare 临时隧道）
pwsh scripts/local-deploy.ps1

# 只看状态
pwsh scripts/local-deploy.ps1 -Status

# 只起后端、不起隧道（内网联调用）
pwsh scripts/local-deploy.ps1 -SkipTunnel

# 停止隧道与后端
pwsh scripts/local-deploy.ps1 -Stop
```

cloudflared 若未安装，用国内可达镜像下载（GitHub 直连会被重置，实测 `curl (56)`）：

```powershell
& "$env:SystemRoot\System32\curl.exe" -L -o D:\ai\prj\trae\HuaWei\MyLangLean\.tools\cloudflared.exe https://ghfast.top/https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
```

### 3.3 数据与日志布局（不污染仓库）

```
D:\AiLearning\
├─ data\postgres\        # Docker 模式 PG 数据（bind mount）
├─ logs\                 # uvicorn / cloudflared 日志
└─ run\local-deploy.json # 进程与公网地址状态，供 -Status / -Stop 使用
```

音频不复制：容器以只读方式挂 `backend/build/question_audio`（15778 个 opus，505.8 MB）。

### 3.4 实测结果（2026-11-19，深圳本地出口）

| 检查项 | 结果 |
|---|---|
| 本地 `/health` | 200 `{"status":"ok","app":"AiLearning API","env":"dev"}` |
| 公网 `/health` | 200；首次 12.8 s（TLS+隧道建连），后续 1.85 s |
| 公网 `/legal/privacy` | 200（免登录，1.85 s） |
| 未鉴权访问 `/api/exams` | **401**（鉴权生效） |
| 学生登录 `POST /api/auth/login` | 200，返回 access_token（注意是 **form-urlencoded + `username` 字段**，不是 JSON） |
| 试卷列表 `/api/exams?grade=1&subject=math` | 200，返回 3 张卷；`x-total-count: 3`；中文标题正常（`1年级数学期末卷`） |
| 听力音频 `/api/learn/questions/15745/audio?kind=listening` | 200，`audio/ogg`，1742 B，公网 1.47 s |
| 读题音频 `/api/learn/questions/4522/audio?kind=reading` | 200，`audio/ogg`，34469 B |
| 音频 ETag 条件请求 | `If-None-Match` → **304**，0 B（Cloudflare 未破坏条件校验） |
| 音频缓存头 | `cache-control: public, max-age=2592000` |

> 音频路径易踩坑：路由前缀是 **`/api/learn/questions/{id}/audio`**（`learn.py` 的 `APIRouter(prefix="/learn")` + `settings.api_prefix`），不是 `/api/questions/...`；写错会得到 FastAPI 默认 `{"detail":"Not Found"}`，与"音频未就绪"的业务错误不同。

### 3.5 已知限制（阶段 0 不能当生产用）

| 限制 | 说明 | 对策 |
|---|---|---|
| 大陆访问时延高 | 经 Cloudflare 海外节点，单请求 1.5–2 s；首连 12.8 s | 只用于功能验证；正式对外必须回到境内直连 ECS |
| 临时域名每次变 | `xxx.trycloudflare.com` 重启即换 | 每次验证前 `-Status` 取新地址，在 App「环境诊断」里改 |
| 无 SLA | quick tunnel 不承诺可用性，Cloudflare 侧限速 | 不作为生产入口 |
| 本机不能休眠 | 电脑关机即断 | 验证窗口内保持开机 |
| 无 Caddy | 阶段 0 由隧道承担 TLS | 阶段 1 用 Caddy，配置见 §4.2 |
| 可选国内替代 | 若大陆访问 Cloudflare 持续不畅 | `-Provider cpolar`（国内节点，需 authtoken）或直接先做阶段 1 |

### 3.6 真机联调（EBG-AN00）

1. App 登录 →「我的」→「环境诊断」→ 服务地址填 `-Status` 输出里的 `https://xxx.trycloudflare.com`（**不带结尾斜杠**）。
2. 保存后回首页：验证学生登录、考试中心筛选（g1 数学应为 3 张）、开考、听力播放、退出重进仍可登录（refresh token）。
3. 若 adb 在线，可先用 `adb logcat` 观察 `Dio` 请求耗时；阶段 0 下 1.5–2 s/请求是预期值。

> 实测环境：本机 adb 当前无设备连接（`adb devices` 为空），真机步骤待设备接入后执行。

---

## 4. 阶段 1：独立 ECS 部署

### 4.1 规格测算（基于实测）

| 资源 | 依据 | 建议 |
|---|---|---|
| 内存 | 现网同构三容器 RSS：api 79.6 / db 14.8 / caddy 14.4 MB；AiLearning 依赖更轻（`requirements.txt` 无 pandas/numpy/TTS） | 单栈 **150–300 MB**；**2C2G 够用，2C4G 更稳** |
| 磁盘 | 镜像（优化后）0.3–0.4 GB + 音频 0.5 GB + PG <0.2 GB + 备份 7 天 + Caddy 日志上限 2 GB + 系统 6 GB | **40 GB ESSD**；20 GB 也够用 |
| 带宽 | 试卷 JSON 与按需音频很轻（50 DAU × 20 题 × 16 KB ≈ 16 MB/天）；痛点是首次全量音频 505.8 MB ≈ 23 分钟/人 | 3 Mbps 可支撑初期；音频走 **OSS+CDN** 或严格按需播放 |
| CPU | 单 uvicorn worker；组卷/体检脚本属批处理 | 2 核够；批处理避峰 |

### 4.2 独立栈架构

```
公网（安全组仅 22/80/443，22 建议限源）
              │
        ┌─────▼─────┐
        │ Caddy 2   │ 80/443，自动 ACME 证书，180 天 JSON 访问日志
        └──┬─────┬──┘
  api.域名 │     │ www.域名（备案首页 HTML）
           ▼     ▼
     ┌──────────────┐   同 compose 自定义网络（建议 ipam 固定 subnet）
     │ api (FastAPI)│   uvicorn 0.0.0.0:8000，不发布宿主端口
     └──────┬───────┘
            ▼
     ┌──────────────┐
     │ db (PG16)    │   internal: true，无宿主端口
     └──────────────┘
     卷：pgdata / caddy_data / question_audio（只读）
```

与阶段 0 的差异只有承载与入口；应用侧不需要改动。

### 4.3 改造清单

| # | 项 | 内容 | 级别 |
|---|---|---|---|
| D1 | 新建实例 | Ubuntu 24.04、2C4G（或 2C2G + 2G swap）、40 GB ESSD、≥3 Mbps；安全组仅 22/80/443 | 阻断 |
| D2 | `scripts/setup-ailearning-ecs.sh` | 复用 RetroEmuPouch `setup-ecs.sh`（阿里云 Docker CE 源、compose v2、镜像加速、git/curl/htop、ufw），**补它缺的三项**：2G swap + `vm.swappiness=10`、时区 `Asia/Shanghai`、fail2ban | 阻断 |
| D3 | `deploy/docker-compose.yml` | 删 `nginx`；加 `caddy`（80/443 + `caddy_data`）；api 不发布宿主端口；db `internal: true`；加 `x-logging` 与 `mem_limit`（api 512m / db 512m）；api 补 healthcheck（现仅 Dockerfile 内有） | 阻断 |
| D4 | `deploy/Caddyfile.prod` | `api.*` / `www.*` / 裸域 301；安全头；`roll_size 50MiB + roll_keep_for 4320h` | 阻断 |
| D5 | `deploy/Caddyfile.staging` | 备案前纯 HTTP `:80`，照搬 RetroEmuPouch `Caddyfile.staging` 模式 | 必须 |
| D6 | `.dockerignore` + Dockerfile 白名单 COPY | 现 `context: ..` 若无 `.dockerignore`，上下文约 **4 GB**（`app/build` 2.7 GB、`backend/build` 884 MB、`.venv` 330 MB、`docs` 80 MB）；`COPY backend/` 还会把它们塞进镜像 | **阻断** |
| D7 | `scripts/deploy-backend.ps1` | 改 **git clone/pull + 服务器构建**（仓库仅 46 MB，3 Mbps 约 2 分钟），替代 scp 887 MB（约 40 分钟、不可续传） | 必须 |
| D8 | `scripts/backup-ailearning-db.sh` + `healthcheck.sh` | 可直接复用现成两个脚本（改库名与 URL）；独立机后 cron 不再需要错峰 | 必须 |
| D9 | 客户端域名注入 | `build-apk.ps1` / `build-hap.ps1` / `ci.ps1` 传 `-ApiBaseUrl https://api.ailearnning.cn`；`app_constants.dart` 仅保底 | 必须 |
| D10 | **生产内容与音频资产** | 见 §5 P0-A / P0-B | 阻断 |

### 4.4 数据库、迁移与备份

- **实例**：独立 `postgres:16-alpine`，volume `ailearning_pgdata`；库/用户 `ailearning`；口令独立。
- **迁移**：`entrypoint.sh` 已执行 `alembic upgrade head`；**当前 head = `d6e7f8g9h0a1`**（比上一版文档多一枚 `listening_play_quota`），表数 **35**。
- **初始化**：`RUN_SEED` 只做底座，**不能当内容交付**（见 §5）。
- **备份**：`pg_dump` 每日 → `/opt/backups/ailearning/db-YYYY-MM-DD.sql.gz`，保留 7 天；**另加异地**（推 OSS，保留 30 天）。
- **恢复演练**：临时库导入比对行数（A13）。
- **审计留存**：`AUDIT_RETENTION_MONTHS=24`。

### 4.5 环境变量

`/opt/ailearning-backend/.env`（600，不入 git）：

```dotenv
POSTGRES_DB=ailearning
POSTGRES_USER=ailearning
POSTGRES_PASSWORD=<openssl rand -hex 24>
JWT_SECRET=<openssl rand -hex 32>          # >=32，validate_settings 强制
CORS_ORIGINS=["https://www.ailearnning.cn"]
LEGAL_PUBLIC_BASE_URL=https://www.ailearnning.cn
RUN_SEED=false
AUDIT_RETENTION_MONTHS=24
APP_DISPLAY_NAME=深爱学
APP_VERSION_LABEL=1.0.0
ICP_RECORD_NO=<备案通过后回填>
APP_RECORD_NO=<备案通过后回填>
SOFTWARE_COPYRIGHT_NO=<软著取得后回填>
SUPPORT_EMAIL=support@ailearnning.cn
FORWARDED_ALLOW_IPS=<caddy 固定网段，如 172.30.0.0/16>
```

> `FORWARDED_ALLOW_IPS` 当前 `entrypoint.sh` 默认 `*`，会信任任意 `X-Forwarded-For`，审计 IP 可伪造；必须显式收窄。

### 4.6 实施步骤

| 阶段 | 内容 | 人日 |
|---|---|---|
| S1 | 开实例 + 安全组 + `setup-ailearning-ecs.sh`（D1/D2） | 0.75 |
| S2 | compose / Caddyfile(prod+staging) / Dockerfile / `.dockerignore`（D3–D6） | 1.0 |
| S3 | `deploy-backend.ps1` + 备份/巡检 cron（D7/D8） | 0.5 |
| S4 | **内容交付**（P0-A） | 1.5–2.0 |
| S5 | **音频交付**（P0-B） | 0.5–1.0 |
| S6 | 备案 + 解析切换 + 正式 HTTPS（P0-C，含外部等待） | 0.5 + 等待 |
| S7 | 压测与 A1–A15 验收 | 0.5 |

顺序纪律：**S1–S3 先在 staging（纯 HTTP）跑通 → S4/S5 灌内容与音频 → 最后 S6 切域名**。内容与音频没解决就切 DNS，等于把空站暴露到公网。

### 4.7 域名与备案

- **拼写必须先核验（P0 阻断）**：用户口径 `ailearnning.cn`（双 n），仓库内既有资产多为 `ailearning.cn`（单 n，见隐私政策、`legal_constants.dart`、`deploy/.env.example`、`k12-learning-app-design.md`）；`docs/` 下同时存在两张证书图。确认后全链路统一（客服邮箱、CORS、法务地址、商店文案）。
- 备案前 80 端口被拦 → ACME 必失败，只能跑 `Caddyfile.staging`（纯 HTTP）或 SSH 隧道验证。
- **换实例是否需要"接入/变更备案"**：同账号同服务商通常只需改解析，但存在被拦风险，按阿里云当期要求核实后再切 DNS。
- `www` 必须能打开 HTML 首页（§4.3 D 系列中的 C5 等价项），当前 `GET /` 只返回 JSON，**不满足备案审核**。

---

## 5. 仍然存在的 3 个 P0（换机器也不会消失）

### P0-A 生产内容初始化 —— ✅ 链路已实现并本地验证（2026-11-19）

**问题**：本地独立库实跑 `scripts.seed` 只有 **146 教材 / 118 章节 / 300 知识点 / 600 题**（choice 213 / fill 205 / judge 182，**无 listening / answer / composition**）+ 9 套蓝图 + 3 套 mock 演示卷；而 dev 库能力是 **18746 题 / 81 张已发布卷 / 1348 道听力题**。按 seed 上线 = 单元/期中/期末卷 0 张。

**已实现方案：受控数据包（导出 → 导入），不走"生产上重跑生成脚本"**

| 脚本 | 作用 |
|---|---|
| `backend/scripts/export_content_pack.py` | 从 dev 库导出 6 张内容表为 `.json.gz`，**只含内容**：textbooks / chapters / knowledge_points / questions / exam_blueprints / exams；显式排除 users、attempts、answers、wrong_questions、mastery、audit、classes、assignments 等全部运行时与用户数据 |
| `backend/scripts/import_content_pack.py` | 按原 id 导入目标库；`--truncate --yes` 清空内容表后全量灌入；无 `--truncate` 时按 id 幂等跳过已存在行；PG 导入后自动 `setval` 回填 sequence；`--dry-run` 只统计 |

**本地实测（2026-11-19）**

| 步骤 | 结果 |
|---|---|
| 导出 | `build/content_pack/ailearning-content-20261119.json.gz`，**1.5 MB**，146 / 726 / 3455 / 18746 / 90 / 81 |
| 导入空库（sqlite，create_all 建表） | 146 / 726 / 3455 / 18746 / 90 / 81 全部一致；自检 published 题 **18746**、published 卷 **81**、听力题 **1348** |
| 幂等重导（再跑一次，不 truncate） | 6 张表**新增 0，全部跳过** |
| 内容门禁 `audit_published_papers` | 81 卷、**issues 0**、info 16（均为 `LEAK_INFO`）、`papers_with_issues 0` |

**生产自检（无账号依赖，可反复跑）**

`backend/scripts/content_selfcheck.py` 只读库、不发 HTTP、不需要学生账号，检查：卷内 `question_id` 可回查、无重复、分值合计与卷面总分一致、题干/答案非空、q_type 合法、g1–g9 × 语数英 × 单元/期中/期末 覆盖矩阵。

本地实测（临时库导入后）：**阻断问题 0 / 警告 0 / 覆盖缺口 0 / 分值不符 0**，题量 18746（judge 2698、choice 5938、fill 4774、answer 2659、multiple 1093、listening 1348、composition 236），published 卷 81（unit 27 / midterm 27 / final 27）。

> 注意 `exam_type` 取值是 **`midterm`**（不是 `mid`），老脚本里写成 `mid` 会误报 27 个覆盖缺口。
> `verify_papers_takeable.py` 依赖 dev 固定学生账号（id=2）与 `http://127.0.0.1:18080`，只能本地用，不要作为生产验收项。

**生产首启顺序（写进部署流程）**

```bash
# 0. 起栈（只跑迁移，不灌 seed）
RUN_SEED=false docker compose up -d
# 1. 账号 bootstrap（空库没有任何账号，不做这步谁也别想登录）
ADMIN_PASSWORD='<强口令>' docker compose exec -T api python -m scripts.bootstrap_admin
# 2. 灌内容包（生产库为空库时也必须带 --truncate 语义确认，实际为空则无副作用）
docker compose exec -T api python -m scripts.import_content_pack \
    --pack /build/content_pack/ailearning-content-20261119.json.gz --truncate --yes
# 3. 门禁：先跑无账号依赖的自检，再跑答案泄漏审计
docker compose exec -T api python -m scripts.content_selfcheck
docker compose exec -T api python -m scripts.audit_published_papers
```

**账号 bootstrap（`backend/scripts/bootstrap_admin.py`）**

- 口令只从环境变量读（`ADMIN_PASSWORD` / `QUALITY_STUDENT_PASSWORD`），不进 shell 历史；
- production 拒绝弱口令（<10 位、纯数字、`admin123`/`student123` 等）；
- 幂等：已存在默认跳过，`--reset-password` 才改口令；
- 顺带同步 RBAC catalog 并回填 `user_roles`（空库第一次跑必须有）。
- 可选质检学生（`QUALITY_STUDENT_PHONE`，默认 `13900000001`）只用于登录态冒烟，`--no-student` 可跳过。

本地实测（临时库）：首次 `roles_created 10 / permissions_created 36 / links_created 94` + 建 admin 与质检学生 + `user_roles 2 条`；重跑全部跳过、`user_roles 0 条`；`APP_ENV=production` + 弱口令 → **exit 2 拒绝**。

> 注意：`RUN_SEED=true` 与数据包二选一。seed 会写入 id 1..N 的占位内容，与数据包 id 段冲突；若已误跑 seed，用 `import_content_pack --truncate --yes` 覆盖即可。
> 数据包不进 git（在 `backend/build/` 下，已被 `.gitignore` 与 `.dockerignore` 排除）；上线时用 `scp`（1.5 MB）或独立传输通道送到 `/opt/ailearning-assets/`。

### P0-B 音频资产 —— 体积与覆盖率已实测，清单/校验工具已就绪

**实测（2026-11-19，`backend/build/question_audio`）**

| 类别 | 文件数 | 体积 |
|---|---|---|
| 读题音频 `audio/xx/*.opus` | 14612 | 499.9 MB |
| 听力音频 `audio/listening/xx/*.opus` | 1166 | 5.9 MB |
| **合计** | **15778** | **505.8 MB** |

> 旧文档写的 1.7 GB 是错的（把中间产物/重复目录也算进去了）；实际 505.8 MB，3 Mbps 下首次传输约 **23 分钟**，volume 挂载方案完全可接受，不需要为体积上 OSS。
> 听力题 **1348 道**共用 **1166 个音频文件**（同文本共享缓存键），覆盖率 **1348/1348 = 100%**。

**工具（`backend/scripts/asset_manifest.py`）**

```bash
# 快速清单（不算哈希，秒级）
python -m scripts.asset_manifest --no-hash --out build/audio_manifest.json
# 传输基线（含 sha256，本地实测 15778 文件全量哈希约 30s）
python -m scripts.asset_manifest --out build/audio_manifest_sha.json
# 传输后校验（rsync/scp 落盘后跑，逐文件 sha256 比对）
python -m scripts.asset_manifest --verify-manifest build/audio_manifest_sha.json \
    --dir /opt/ailearning-assets/question_audio
```

本地实测：清单 15778 个文件、`--verify-manifest` **异常 0**；听力覆盖 100%。

**交付路径（二选一，仍待决策）**

- **volume 只读挂载 + 一次性 rsync**（`--partial --append-verify`，505.8 MB / 3 Mbps ≈ 23 分钟），落 `/opt/ailearning-assets/question_audio`；
- **OSS + CDN**（同区域内网传输不计流量，Caddy 改为重定向）。

两种方式都必须跑一次 `--verify-manifest` 才算交付完成。不定义这条，读题降级系统 TTS、**听力题无兜底**。

### P0-C 备案与解析

见 §4.7。它是时间上的阻断，不是技术阻断。

---

## 6. 验收标准

| # | 验收项 | 判定 |
|---|---|---|
| A1 | 独立栈隔离 | 本机只有 AiLearning 栈，无端口冲突；与 RetroEmuPouch 零影响（不再有"同机共存"要求） |
| A2 | API 内网可达 | `http://127.0.0.1:18080/health` → `status=ok` |
| A3 | 公网 HTTPS | `https://api.ailearnning.cn/health` 200；`www/legal/privacy` 浏览器可直接打开且免登录 |
| A4 | 证书自动 | Caddy 自动签发/续期，无手工 certs |
| A5 | 数据隔离与恢复 | 独立库/备份/日志；`pg_dump` 可导入临时库 |
| A6 | 迁移正确 | `alembic current` = **`d6e7f8g9h0a1`**；**35 表**；seed 幂等 |
| A7 | 生产配置合规 | `validate_settings` 通过（JWT 自定义、DEBUG=false、AUTO_CREATE_TABLES=false、CORS 白名单） |
| A8 | 安全组 | 公网仅 22/80/443；18080/5432 外网不可达；22 限源或 fail2ban 生效 |
| A9 | 日志留存 | Caddy JSON 访问日志 180 天轮转生效 |
| A10 | 客户端联通 | 正式构建的真机登录、组卷、提交、听力播放全链路通过 |
| **A11** | **内容完整性** | 每级每科 9 张卷（81 张）、题量合计 2088、0 硬问题 |
| **A12** | **音频可用** | `kind=reading` / `kind=listening` 均 200（或 OSS 302）；命中缓存返 304 |
| **A13** | **备份可恢复** | 临时库导入后行数与生产一致 |
| **A14** | **幂等重建** | 重复 deploy/seed 不产生重复卷、不重复建卷 |
| **A15** | **压测** | 50 并发开考 P95 < 2 s，内存峰值 < 70% |

> 阶段 0 已完成 A2/A3（临时域名）/A5（SQLite）/A7 的部分：A3 用 trycloudflare 域名验证，A6 以 dev 库 35 表为准。

---

## 7. 运维与回滚

- **日常更新**：git pull → `docker compose build api` → `up -d api`；只传代码与迁移，不覆盖 `.env`。
- **Caddy 变更纪律**：`caddy validate` → 变更后验 api/www 双侧 → 改端口/volume 时用 `up -d --force-recreate caddy`（`restart` 不应用 `extra_hosts`/网络变更）。
- **回滚**：① 客户端切回旧 `API_BASE_URL` 重新发版（提前留旧包）；② 服务端 `git checkout <上一个 tag>` + 重建 api；③ DNS 切回。
- **监控**：host cron 每 10 分钟 `curl /health`，失败写 `/var/log/ailearning-health.log`；磁盘与 swap 纳入每周检查。
- **阶段 0 的运维**：本机保持不休眠；每次重启后 `-Status` 取新地址并同步给测试同学。

---

## 8. 风险登记

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| 域名拼写双/单 n 混用 | 高 | 高 | 先核验再全链路统一 |
| 单点无冗余 | 中 | 高 | 异地备份（OSS 30 天）+ 每日巡检 + 快速重建脚本 |
| 新机安全基线不足 | 中 | 高 | 密钥登录、禁密码、fail2ban、22 限源、仅 80/443 |
| `FORWARDED_ALLOW_IPS=*` 伪造审计 IP | 高 | 中 | 显式收窄到 Caddy 网段 |
| 备案未过 80 被拦、ACME 失败 | 高 | 中 | staging 纯 HTTP 先跑；备案+解析生效后切正式 |
| 生产内容为空（seed 只有 600 题） | 高 | 高 | P0-A 受控导入 + 三层门禁 |
| 音频未交付导致听力不可用 | 高 | 高 | P0-B 二选一交付；OSS+CDN 优先 |
| 2C2G 内存吃紧 | 中 | 中 | 2C4G 或 2G swap；`mem_limit`；单 worker |
| 大陆访问 Cloudflare 慢（阶段 0） | 高 | 低 | 仅验证用；正式回境内直连 |

---

## 9. 任务衔接与实现进度

- 对应 `release-plan.md` 缺口 2/3/4、`project-task-plan.md` R-02/R-03/R-06。

### 9.1 已落地（2026-11-19）

| 项 | 文件 | 状态 |
|---|---|---|
| 阶段 0 一键部署 | `scripts/local-deploy.ps1` | **已实测**（见 §3.4） |
| 阶段 0 本地栈 | `deploy/docker-compose.local.yml`、`deploy/.env.local.example` | 已写（本机无 Docker，走 uvicorn 路径实测） |
| C5 备案首页 | `backend/app/main.py` 根路由支持 `Accept: text/html` | **已实测**：HTML 200 / 1763 B，默认仍返回 JSON |
| D2 实例初始化 | `scripts/setup-ailearning-ecs.sh` | 已写（swap/时区/Docker 阿里云源/镜像加速/fail2ban），待实例实测 |
| D3 生产 compose | `deploy/docker-compose.yml`（db/api/caddy + internal/edge 双网络 + mem_limit + 日志轮转） | 已写，YAML 校验通过，待实例 `up` 实测 |
| D4/D5 Caddyfile | `deploy/Caddyfile.prod`、`deploy/Caddyfile.staging`、`deploy/docker-compose.staging.yml` | 已写，待 `caddy validate` |
| D6 构建瘦身 | `.dockerignore` + `Dockerfile` 白名单 COPY（源码约 2 MB，替代原 884 MB 的 `backend/`） | 已完成，待实测镜像体积 |
| D7 部署脚本 | `scripts/deploy-backend.ps1`（setup/deploy/seed/status/logs/stop/assets，git 拉取 + 服务器构建） | 已写，待实例实测 |
| P0-A 内容导出 | `backend/scripts/export_content_pack.py` | **已实测**：81 卷 / 18746 题 / 包体 1.5 MB |
| P0-A 内容导入 | `backend/scripts/import_content_pack.py` | **已实测**：空库一致、幂等重导 0 新增、audit 0 issues |
| P0-A 内容自检 | `backend/scripts/content_selfcheck.py` | **已实测**：阻断 0 / 警告 0 / 覆盖缺口 0 / 分值不符 0 |
| 账号 bootstrap | `backend/scripts/bootstrap_admin.py` | **已实测**：建号/幂等/弱口令拒绝（exit 2） |
| P0-B 音频清单 | `backend/scripts/asset_manifest.py` | **已实测**：15778 文件 / 505.8 MB / 听力覆盖 100% / 校验 0 异常 |

### 9.2 待用户决策（阻塞上线，不阻塞验证）

1. 域名拼写：`ailearnning.cn` 还是 `ailearning.cn`（影响客服邮箱、CORS、法务、商店文案全链路）；
2. 独立实例规格与预算（2C2G + 2G swap vs 2C4G）；
3. 音频交付方式（volume 挂载 vs OSS+CDN）；
4. 生产内容交付形态（受控数据包 vs 把导入 + 组卷纳入流水线）。

### 9.3 本轮遗留

- 真机走查未执行：`adb devices` 当前无设备；真机验证步骤见 §3.6，可等设备接入后补。
- `Caddyfile.prod` 仅做结构核对，未跑 `caddy validate`（本机无 caddy 与 docker）。

---

## 附录 A：2026-11-19 实测证据

**A-1 服务器（RetroEmuPouch 现网，用于规格参照）**：内存 1740 MB（used 652 / available 1088），swap 2 GB 已用 242 MB；磁盘 40 G 用 6.6 G；Docker 29.9.3；时区已 CST；三容器 RSS 109 MB。

**A-2 共用方案网络拓扑证伪**：ECS 上分别监听 `127.0.0.1:18099` 与 `0.0.0.0:18098`，从 `caddy:2-alpine` 容器经 `host.docker.internal`（解析为 172.17.0.1）访问：loopback **UNREACHABLE**、`0.0.0.0` **REACHABLE**。docker-proxy 只监听 loopback，容器侧无监听。→ 共用方案的 `reverse_proxy host.docker.internal:18080` 不成立；独立方案同 compose 反代 `api:8000` 无此问题。

**A-3 构建与仓库体积**：构建上下文 ≈ 4 GB（`app/build` 2731 MB、`backend/build` 884 MB、`.venv` 330 MB、`docs` 80 MB、db 18.9 MB）；git 仓库 45.9 MB / 跟踪 2814 文件 82.4 MB；音频与 `*.db` 均被 `.gitignore` 排除（`backend/build/*` 跟踪数 0）。

**A-4 seed 实跑（独立 sqlite，已删探测库）**：146 教材 / 118 章节 / 300 知识点 / 600 题（choice 213·fill 205·judge 182）/ 9 蓝图 / 3 套 `is_past_paper=0, source=mock` 演示卷。学科分布 chinese 126、english 126、math 126、politics 72、history 36、physics/biology/geography 各 30、chemistry 24。

**A-5 迁移与表**：`alembic heads` = `d6e7f8g9h0a1`；dev 库表数 35。

**A-6 阶段 0 本地实测**：见 §3.4（含公网时延与 304）。

**A-7 音频资产**：`backend/build/question_audio` 递归 15778 个 `.opus`（读题 14612 / 499.9 MB，听力 1166 / 5.9 MB），合计 **505.8 MB**（另有 4 个 json + 1 个 md 报告）。听力题 1348 道，覆盖 1348/1348 = 100%。

> 本文基于对两个仓库代码、ECS 只读命令与本机实跑的核对（2026-11-19）；平台政策、证书与备案要求以当期官方公告为准。
