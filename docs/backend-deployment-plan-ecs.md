# 深爱学（AiLearning）后端服务同机部署方案

> **文档性质**：后端生产部署实施方案（与 `release-plan.md` 缺口 2/3/4 配套）
> **目标环境**：阿里云 ECS `112.74.114.146`（与 RetroEmuPouch 账号后端同一台）
> **目标域名**：`ailearnning.cn`（见 §2.1 拼写核验）
> **方案基线**：复用 RetroEmuPouch `tools/account_backend` 已验证的 Docker Compose + Caddy + PostgreSQL + Alembic 部署模式
> **最后更新**：2026-11-17
> **关联文档**：`docs/release-plan.md`、`docs/skills.md` §5.6、`docs/project-task-plan.md`（R-02/R-03/R-06）

---

## 1. 结论速览

| 维度 | 结论 |
|---|---|
| 同机可行性 | **可行**。ECS 2C2G 上再跑一套 FastAPI + PostgreSQL，内存增量约 180 MiB；先补 2G swap 后可稳定承载 |
| 公网入口 | 复用 RetroEmuPouch 已有的 **Caddy 容器**（独占 80/443），AiLearning **不再自建 nginx**，避免端口冲突 |
| 域名 | `api.ailearnning.cn`（App API）+ `www.ailearnning.cn`（法务/备案首页）；裸域 301 跳转 |
| 数据库 | AiLearning **独立** PostgreSQL 容器 + 独立 volume，不共用 RetroEmuPouch 的库与网络 |
| 网络隔离 | AiLearning API 只绑 `127.0.0.1:18080`；DB 完全不映射宿主端口 |
| 备案/HTTPS | 备案前走 SSH 隧道内网验证；备案通过后由 Caddy 自动签发证书（Let's Encrypt），不再手工放 certs |
| 主要风险 | ① 域名拼写 `ailearnning` vs 项目内既有 `ailearning` 不一致；② Caddy 配置误覆盖会打断 RetroEmuPouch；③ 备案未过前 80 端口不可用；④ 2C2G 内存需先补 swap |

---

## 2. 现状与约束

### 2.1 域名拼写必须先核验（P0 阻断）

用户指定域名为 **`ailearnning.cn`（双 n）**，但项目内既有资产普遍写作 **`ailearning.cn`（单 n）**：

- `backend/app/legal/privacy.md` L192、`app/lib/core/constants/legal_constants.dart` L9、`deploy/.env.example` L25、`docs/k12-learning-app-design.md` L34 等均为 `ailearning.cn` / `AiLearning.cn`；
- `docs/ailearnning.cn_certificate.png`（双 n）与 `docs/ailearning.com_certificate.png` 同时存在。

**行动**：确认实际注册/可备案的域名。本方案以下统一按 **`ailearnning.cn`** 编写；若实际为 `ailearning.cn`，全文替换即可，但必须同步修改客服邮箱、CORS、法务地址、商店文案，保证全链路一致。

### 2.2 RetroEmuPouch 已验证的部署资产（直接复用模式）

来源：`D:\ai\prj\trae\HuaWei\RetroEmuPouch\tools\account_backend\`、`docs\design-account-backend.md`

| 组件 | RetroEmuPouch 现状 | AiLearning 复用方式 |
|---|---|---|
| ECS | `112.74.114.146`，Ubuntu 24.04.5，2C2G/40GB/3Mbps，安全组仅 22/80/443 | 同一台，不新增实例 |
| 容器编排 | `docker-compose.prod.yml`，3 容器：`db` / `app` / `caddy`；`restart: always`；`json-file` 日志轮转 10m×3 | 同样的 compose 结构（但去掉自身 caddy） |
| 反向代理 | `caddy:2-alpine` 独占 80/443，`Caddyfile.prod` 按 Host 路由 `api.`/`www.`，自动 HTTPS，访问日志 180 天留存 | **共用这个 Caddy**，新增 AiLearning 两个 site 块 |
| 数据库 | `postgres:16-alpine`，`internal` 网络，无宿主端口；`alembic upgrade head`；03:15 每日 `pg_dump` 备份 7 天 | 同版本独立实例，独立 volume/凭据/备份 |
| 部署脚本 | `scripts/deploy.ps1`（setup/deploy/seed/update/logs/stop，-Staging/-Domain），SSH key `C:\Users\liuzhixing\.ssh\id_ecs99` | 复制模式新建 `scripts/deploy-backend.ps1` |
| 健康检查 | `GET /healthz`；host cron 每 10 分钟 `healthcheck.sh` | 新增 AiLearning `/health` 检查，错开时间 |
| 安全 | JWT/DB 口令 env 注入、CORS 白名单、`*`/localhost 被 `validate_settings` 拒绝 | AiLearning 已有同等校验（`backend/app/core/config.py` L82-107） |

### 2.3 AiLearning 现状（与 RetroEmuPouch 的关键差异）

- 已有 `deploy/Dockerfile`、`deploy/docker-compose.yml`、`deploy/entrypoint.sh`、`deploy/nginx/ailearning.conf`、`.env.example`（**已具备生产化骨架**）。
- 但 `deploy/docker-compose.yml` L34-44 的 `nginx` 服务**硬绑定宿主 80/443**，与 RetroEmuPouch 的 Caddy **直接冲突**：必须删除该服务。
- `deploy/nginx/ailearning.conf` L12 `server_name _;` 仍是占位；证书目录 `deploy/certs/` 为手工证书模式，需改为 Caddy 自动证书。
- `entrypoint.sh` 已做 `alembic upgrade head` + 可选 seed，单 uvicorn worker，符合 2C2G 约束。
- 生产校验 `validate_settings()` 已覆盖 JWT 默认密钥、DEBUG、AUTO_CREATE_TABLES、CORS 通配等，可直接沿用。
- 质量门禁：`pytest` 440 通过、`flutter test` 174 通过、`ruff`/`analyze` 干净（见 `docs/skills.md` L691-692）。

---

## 3. 总体架构

```
                          公网（安全组仅 22/80/443）
                                      │
                       ┌──────────────▼──────────────┐
                       │  共享 Caddy（RetroEmuPouch   │
                       │  compose 的 caddy 容器）      │
                       │  80/443 + 自动 HTTPS/ACME    │
                       └───┬──────────────────┬───────┘
        api.gamepouch.cn   │                  │   api.ailearnning.cn
        www.gamepouch.cn   │                  │   www.ailearnning.cn
                           │                  │
                 reverse_proxy app:8000   reverse_proxy host.docker.internal:18080
                           │                  │
        ┌──────────────────▼───────┐   ┌──────▼──────────────────────┐
        │ RetroEmuPouch stack      │   │ AiLearning stack            │
        │ /opt/retroemupouch-account│   │ /opt/ailearning-backend     │
        │ app:8000 / db:5432       │   │ api:127.0.0.1:18080→8000    │
        │ 网络 internal + web      │   │ db:5432（无宿主映射）        │
        └──────────────────────────┘   │ 网络 ailearning_internal    │
                                       └─────────────────────────────┘
```

### 3.1 端口与域名矩阵

| 项 | RetroEmuPouch（现状） | AiLearning（本方案） |
|---|---|---|
| 公网域名 | `api.gamepouch.cn` / `www.gamepouch.cn` | `api.ailearnning.cn` / `www.ailearnning.cn` |
| 公网端口 | Caddy 80/443 | **共用同一 Caddy**，不新开端口 |
| API 容器内端口 | 8000 | 8000 |
| API 宿主映射 | 无 | `127.0.0.1:18080:8000`（仅 loopback） |
| DB 容器 | `postgres:16-alpine` 5432 | `postgres:16-alpine` 5432 |
| DB 宿主映射 | 无 | 无 |
| Caddy→API | `app:8000`（同 compose 网络） | `host.docker.internal:18080`（跨 compose，经宿主 loopback） |
| 健康检查 | `GET /healthz` | `GET /health` |

> **为何选 loopback 而非共享 Docker 网络**：两个 compose 项目各自独立，不依赖对方的网络名（避免 `retroemupouch-account_web` 这类隐式耦合）。代价是 Caddy 需增加一行 `extra_hosts: host.docker.internal:host-gateway`（Docker 20.10+ 支持，当前 Docker 29.9.3 满足）。

---

## 4. 代码与配置改造清单（动手前先做）

| # | 文件（AiLearning 仓库） | 改造内容 | 必要性 |
|---|---|---|---|
| C1 | `deploy/docker-compose.yml` | **删除 `nginx` 服务**；`api` 增加 `ports: ["127.0.0.1:18080:8000"]`；补 `LEGAL_PUBLIC_BASE_URL`、`ICP_RECORD_NO`、`APP_RECORD_NO`、`SOFTWARE_COPYRIGHT_NO`、`AUDIT_RETENTION_MONTHS`、`FORWARDED_ALLOW_IPS`；加日志轮转锚点与 `mem_limit`（建议 api 768m / db 512m） | **阻断**（端口冲突） |
| C2 | `deploy/Dockerfile` | pip 改阿里云镜像（对齐 RetroEmuPouch）；可选加非 root 用户 | 建议（大陆拉取速度） |
| C3 | 新增 `.dockerignore`（仓库根） | 排除 `backend/*.db*`、`docs/`、`.tools/`、`build/`、`app/build/` 等，避免构建上下文膨胀 | 建议 |
| C4 | `deploy/.env.example` | 域名占位改 `ailearnning.cn`；`CORS_ORIGINS=["https://www.ailearnning.cn"]`；`LEGAL_PUBLIC_BASE_URL=https://www.ailearnning.cn` | 必须 |
| C5 | `backend/app/main.py` | 根路径 `GET /`：当 `Accept: text/html` 时返回简易 HTML 落地页（含隐私政策/用户协议链接），满足备案「首页 URL 可访问」要求；JSON 行为保持不变 | 必须（备案） |
| C6 | `scripts/deploy-backend.ps1`（新建） | 参照 RetroEmuPouch `deploy.ps1`，实现 setup/deploy/seed/update/logs/stop/ssh，复用 `$env:ECS_SSH_KEY` | 必须 |
| C7 | RetroEmuPouch `tools/account_backend/docker-compose.prod.yml` | `caddy` 服务加 `extra_hosts: ["host.docker.internal:host-gateway"]` | 必须 |
| C8 | RetroEmuPouch `tools/account_backend/Caddyfile.prod` | 新增 AiLearning 两个 site 块 + HTTP→HTTPS 跳转 + 180 天访问日志（见 §5.2） | 必须 |
| C9 | `scripts/build-apk.ps1` / `build-hap.ps1` / `ci.ps1` | 生产构建传 `-ApiBaseUrl https://api.ailearnning.cn`；`ci.ps1` L30 默认值改正式域名 | 必须（客户端） |
| C10 | `app/lib/core/constants/app_constants.dart` L48-51 | `API_BASE_URL` 默认值仅用于本地调试；生产一律由 dart-define 注入。**备案号**优先走后端 `/app/info` 云端下发，避免硬编码发版 | 建议 |

---

## 5. Caddy 同机共存配置

### 5.1 前置改动（C7）：让 Caddy 能访问宿主 loopback

在 RetroEmuPouch `docker-compose.prod.yml` 的 `caddy` 服务中加入：

```yaml
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

> ⚠️ 该文件由 RetroEmuPouch `deploy.ps1 -Action deploy` 上传；`-Action update` **故意不覆盖** compose/Caddyfile/env（2026-11-05 事故教训）。因此此改动必须走完整的 `-Action deploy`，并在变更前备份远端文件。

### 5.2 Caddyfile 追加片段（C8）

```caddyfile
# ── 深爱学 AiLearning（同机第二域名）──
api.ailearnning.cn {
    reverse_proxy host.docker.internal:18080
    handle /health {
        reverse_proxy host.docker.internal:18080
    }
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
    log {
        output file /data/logs/ailearning-access.log {
            roll_size 50MiB
            roll_keep 20
            roll_keep_for 4320h
        }
        format json
    }
}

www.ailearnning.cn {
    reverse_proxy host.docker.internal:18080
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "SAMEORIGIN"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
    log {
        output file /data/logs/ailearning-www-access.log {
            roll_size 50MiB
            roll_keep 20
            roll_keep_for 4320h
        }
        format json
    }
}

http://api.ailearnning.cn {
    redir https://api.ailearnning.cn{uri} permanent
}
http://www.ailearnning.cn {
    redir https://www.ailearnning.cn{uri} permanent
}
ailearnning.cn {
    redir https://www.ailearnning.cn{uri} permanent
}
http://ailearnning.cn {
    redir https://www.ailearnning.cn{uri} permanent
}
```

要点：
- CORS 由各后端 `CORSMiddleware` 统一处理，Caddy **不重复设置**（与 RetroEmuPouch 一致）。
- 请求体大小由后端限制；Caddy v2 无 `client_max_body_size`。
- 日志落到 `caddy_data` 卷的 `/data/logs`，满足公安联网备案 6 个月留存；与 `gamepouch.cn` 的日志文件分开，便于取证。

---

## 6. 数据库、迁移与备份

- **实例**：AiLearning 独立 `postgres:16-alpine`，volume `ailearning_pgdata`（与 RetroEmuPouch `pgdata` 完全隔离），库名/用户 `ailearning`，口令由 `/opt/ailearning-backend/.env` 提供（与 RetroEmuPouch `DB_PASSWORD` 不同）。
- **迁移**：`entrypoint.sh` 已执行 `alembic upgrade head`；当前 Alembic 单链 head 为 `c5d6e7f8g9h0`（`backend/alembic/versions/c5d6e7f8g9h0_exam_review.py`），无分叉。生产 `AUTO_CREATE_TABLES=false`。
- **初始化**：首次 `RUN_SEED=true` 起 `python -m scripts.seed`（幂等，134 教材 / 564 题底座）；之后保持 `false`。
- **备份**：新增 `scripts/backup-ailearning-db.sh`，`pg_dump -U ailearning ailearning | gzip > /opt/backups/ailearning/db-YYYY-MM-DD.sql.gz`，保留 7 天；cron 设在 **03:20**（错开 RetroEmuPouch 的 03:15）。
- **恢复演练**：沿用 RetroEmuPouch `migrate-db.sh --restore-drill` 思路，用临时库导入并比对 33 张表行数。
- **审计留存**：`AUDIT_RETENTION_MONTHS=24`（≥6）；`prune_audit` 定时清理。

---

## 7. 环境变量与密钥

`/opt/ailearning-backend/.env`（权限 600，不入 git）：

```dotenv
POSTGRES_DB=ailearning
POSTGRES_USER=ailearning
POSTGRES_PASSWORD=<openssl rand -hex 24>
JWT_SECRET=<openssl rand -hex 32>          # 必须 >=32，validate_settings 会强制校验
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
FORWARDED_ALLOW_IPS=<Caddy 容器在 docker 网桥的地址段>
```

> `SUPPORT_EMAIL` 必须与隐私政策/用户协议/商店素材中的邮箱一致；当前仓库内是 `support@ailearning.cn`（单 n），**随域名核验一并统一**。

---

## 8. 分阶段实施步骤

### P0 — 本机准备（备案前，不影响 RetroEmuPouch）

1. 核验域名拼写（§2.1），完成 `ailearnning.cn` 的 ICP 备案材料准备（与 APP 备案是两回事）。
2. ECS 补 2G swap + `vm.swappiness=10` + 时区 `Asia/Shanghai`（RetroEmuPouch 文档 D2 仍为待办，本方案的前置条件）。
3. 在本地完成 C1~C4、C6 改造，跑质量门禁：
   ```powershell
   cd backend; .\.venv\Scripts\python.exe -m pytest -q
   .\.venv\Scripts\python.exe -m ruff check --select E9,F app alembic tests
   ```
4. 新建 `/opt/ailearning-backend`，上传 `deploy/` 与 `backend/`，填 `.env`，`chmod 600`。

### P1 — 内网部署与验证（备案前，无公网域名）

```powershell
$env:ECS_HOST='112.74.114.146'; $env:ECS_USER='root'
$env:ECS_SSH_KEY='C:\Users\liuzhixing\.ssh\id_ecs99'
powershell -ExecutionPolicy Bypass -File scripts\deploy-backend.ps1 -Action deploy
powershell -ExecutionPolicy Bypass -File scripts\deploy-backend.ps1 -Action seed
```

ECS 上验证（不经过 Caddy）：

```bash
curl -fsS http://127.0.0.1:18080/health
curl -fsS http://127.0.0.1:18080/legal/privacy -H 'Accept: text/html' | head
docker compose -f /opt/ailearning-backend/docker-compose.yml ps
docker compose -f /opt/ailearning-backend/docker-compose.yml logs api
```

也可从本机经 SSH 隧道验证：`ssh -N -L 18080:127.0.0.1:18080 root@112.74.114.146`。

### P2 — 备案通过后的公网切换（与 RetroEmuPouch 协同）

1. DNS：`api`、`www` 两条 A 记录指向 `112.74.114.146`。若使用 Cloudflare，**必须灰云（DNS only）**，不能代理。
2. 备份 RetroEmuPouch 远端 `Caddyfile.prod` 与 compose；应用 C7+C8 改动。
3. **先校验再重载**：
   ```bash
   docker compose -f /opt/retroemupouch-account/docker-compose.prod.yml exec -T caddy caddy validate --config /etc/caddy/Caddyfile
   ```
4. 切 Caddy 到正式配置（含两个项目的 site 块），`docker compose ... restart caddy`，等待 15s。
5. 验证两个域名互不干扰：
   ```bash
   curl -fsS https://api.gamepouch.cn/healthz
   curl -fsS https://api.ailearnning.cn/health
   curl -fsSI https://www.ailearnning.cn/legal/privacy | head
   ```
6. 观察 Caddy ACME 证书签发日志（`/data/logs` 与 `docker logs caddy`），确认两个域名证书均签发成功。

### P3 — 客户端发版

```powershell
powershell -ExecutionPolicy Bypass -File scripts\ci.ps1 `
  -ApiBaseUrl https://api.ailearnning.cn -BuildAab -WithHap
```

- 备案号取得后回填后端 `.env`（`/app/info` 云端下发）与 `app_constants.dart`（离线展示兜底）。
- Android release 禁止明文流量，`network_security_config` 保持仅 HTTPS。

---

## 9. 验收标准

| # | 验收项 | 判定 |
|---|---|---|
| A1 | 同机双栈共存 | 两套 compose 同时 `up`，`docker ps` 无端口冲突，RetroEmuPouch 38 项 smoke 全绿 |
| A2 | API 内网可达 | `http://127.0.0.1:18080/health` 返回 `status=ok` |
| A3 | 公网 HTTPS | `https://api.ailearnning.cn/health` 200，`www/legal/privacy` 浏览器可直接打开且无需登录 |
| A4 | 证书自动 | Caddy 为两个域名自动签发/续期证书，无手工 certs |
| A5 | 数据隔离 | AiLearning 的库/备份/日志与 RetroEmuPouch 完全分开；`pg_dump` 可恢复 |
| A6 | 迁移正确 | `alembic current` = `c5d6e7f8g9h0`；33 表齐备；种子数据幂等 |
| A7 | 生产配置合规 | `validate_settings` 通过；JWT 自定义、DEBUG=false、AUTO_CREATE_TABLES=false、CORS 白名单 |
| A8 | 安全组 | 公网仅 22/80/443；18080/5432 无法从外网访问 |
| A9 | 日志留存 | Caddy JSON 访问日志 180 天轮转配置生效 |
| A10 | 客户端联通 | 用 `https://api.ailearnning.cn` 构建的 APK/HAP 真机登录、组卷、提交全链路通过 |

---

## 10. 运维与回滚

- **日常更新**：AiLearning 用 `-Action update`（只传 `Dockerfile`/`requirements.txt`/`alembic/`/`app/`），**不覆盖 compose/Caddyfile/.env**——沿用 RetroEmuPouch 的事故教训。
- **Caddy 变更纪律**：任何 site 块修改先 `caddy validate`，再重启；变更前备份 Caddyfile，变更后立刻验两个域名。
- **回滚**：
  1. 客户端：切回旧 `API_BASE_URL` 重新发版（需提前保留旧包）；
  2. 服务端：恢复备份的 Caddyfile → 删掉 AiLearning site 块 → `restart caddy` → `docker compose -f /opt/ailearning-backend/docker-compose.yml down`；
  3. DNS：A 记录切回原值（若走 Cloudflare Tunnel 则恢复代理）。
- **监控**：新增 host cron `curl /health` 每 10 分钟（如 `:05` 错开 RetroEmuPouch），失败写 `/var/log/ailearning-health.log`；数据盘用量与 swap 使用率纳入每周检查。

---

## 11. 风险登记

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| 域名拼写 `ailearnning` / `ailearning` 混用 | 高 | 高 | P0 核验并全仓库统一；证书文件、邮箱、CORS、商店文案一并核对 |
| 改 Caddy 打断 RetroEmuPouch 现网 | 中 | 高 | 备份 + `caddy validate` + 分批切换；`-Action update` 不覆盖配置 |
| ICP 备案未过，80 端口被拦截导致 ACME 失败 | 高 | 中 | 备案前只跑 P1 内网验证；备案+DNS 生效后再切正式 Caddyfile |
| 2C2G 内存吃紧 | 中 | 中 | 先补 2G swap；api/db 加 mem_limit；单 uvicorn worker；Caddy 只读静态口 |
| RetroEmuPouch `-Action deploy` 覆盖本地改动 | 中 | 中 | C7 改动纳入 RetroEmuPouch 本地文件并登记变更；部署后核对 `extra_hosts` |
| 跨 compose 走宿主 loopback 排障复杂 | 中 | 低 | 明确 `host.docker.internal:host-gateway`；Caddy 日志按域名分文件 |
| 独立 Postgres 增加运维面 | 中 | 低 | 备份 cron 错峰、恢复演练、凭据独立轮换 |

---

## 12. 任务衔接与下一步

- 本方案对应 `docs/release-plan.md` 缺口 2（隐私 URL）、缺口 3（后端生产化）、缺口 4（备案）的技术落地；对应 `project-task-plan.md` R-02/R-03/R-06。
- 建议按项目管控要求将 §4 的 C1~C10 登记为新任务（暂拟 `BE-01~BE-10`），走 `TODO → DOING → DONE`，并纳入质量门禁验收 A1~A10。
- **当前下一步（阻断）**：确认 `ailearnning.cn` 是否已完成 ICP 备案、DNS 当前指向、是否使用 Cloudflare；确认后即可进入 P0。

> 本文基于对两个仓库实际代码的审阅（2026-11-17）；平台政策、证书与备案要求以当期官方公告为准。
