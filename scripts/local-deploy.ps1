# =================================================================
# AiLearning —— 本地部署 + 内网穿透（Cloudflare Tunnel / CPolar）
#
# 定位：独立 ECS 生产部署前的「真机链路验证」通道。
#       本机跑真实后端（Docker 优先，无 Docker 时回退 uvicorn），
#       用隧道把 127.0.0.1:18080 映射成公网 HTTPS，App 里直接改服务地址即可。
#
# 参考 RetroEmuPouch：tools\account_backend\scripts\tunnel.ps1（同样的双路径 + D 盘数据根）
#
# 用法：
#   pwsh scripts/local-deploy.ps1                 # 启动后端 + Cloudflare 临时隧道
#   pwsh scripts/local-deploy.ps1 -SkipTunnel     # 只起本地后端
#   pwsh scripts/local-deploy.ps1 -Provider cpolar
#   pwsh scripts/local-deploy.ps1 -Status         # 看当前状态与公网地址
#   pwsh scripts/local-deploy.ps1 -Stop           # 停止隧道与本地后端
#
# 前置：cloudflared.exe（放 tools 目录或 PATH），首次可用镜像下载：
#   curl.exe -L -o <tools>\cloudflared.exe https://ghfast.top/https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
# =================================================================
param(
    [int]$LocalPort = 18080,
    [ValidateSet("cloudflare", "cpolar", "none")]
    [string]$Provider = "cloudflare",
    [switch]$SkipTunnel,
    [switch]$Stop,
    [switch]$Status,
    [switch]$ForceRebuild
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DeployDir = Join-Path $ProjectRoot "deploy"
$BackendDir = Join-Path $ProjectRoot "backend"
$ComposeFile = Join-Path $DeployDir "docker-compose.local.yml"
$EnvFile = Join-Path $DeployDir ".env.local"
$EnvExample = Join-Path $DeployDir ".env.local.example"

# 数据根：与应用仓库分离，避免污染 git 工作区
$DataRoot = "D:\AiLearning"
$RunDir = Join-Path $DataRoot "run"
$LogDir = Join-Path $DataRoot "logs"
$StateFile = Join-Path $RunDir "local-deploy.json"
$TunnelLog = Join-Path $LogDir "cloudflared.log"
$UvicornOut = Join-Path $LogDir "uvicorn.out.log"
$UvicornErr = Join-Path $LogDir "uvicorn.err.log"

foreach ($d in @($DataRoot, $RunDir, $LogDir, (Join-Path $DataRoot "data\postgres"))) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

function Write-Step($msg) { Write-Host "▶ $msg" -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host "✅ $msg" -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "⚠️  $msg" -ForegroundColor Yellow }
function Write-Err2($msg) { Write-Host "❌ $msg" -ForegroundColor Red }

# =================================================================
# 状态读取 / 停止
# =================================================================
function Read-State {
    if (Test-Path $StateFile) {
        try { return Get-Content $StateFile -Raw | ConvertFrom-Json } catch { return $null }
    }
    return $null
}

function Stop-All {
    $state = Read-State
    if (-not $state) { Write-Warn2 "没有找到部署状态记录"; return }

    if ($state.tunnelPid) {
        try { Stop-Process -Id ([int]$state.tunnelPid) -Force -ErrorAction Stop; Write-Ok "隧道已停止 (pid $($state.tunnelPid))" }
        catch { Write-Warn2 "隧道进程已不存在" }
    }
    if ($state.backendMode -eq "docker") {
        $docker = Get-Command docker -ErrorAction SilentlyContinue
        if ($docker) {
            & docker compose -f $ComposeFile --env-file $EnvFile down 2>&1 | Select-Object -Last 3
            Write-Ok "Docker 栈已停止"
        }
    } elseif ($state.backendPid) {
        try { Stop-Process -Id ([int]$state.backendPid) -Force -ErrorAction Stop; Write-Ok "uvicorn 已停止 (pid $($state.backendPid))" }
        catch { Write-Warn2 "uvicorn 进程已不存在" }
    }
    Remove-Item $StateFile -Force -ErrorAction SilentlyContinue
}

function Show-Status {
    $state = Read-State
    $health = "不可达"
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$LocalPort/health" -TimeoutSec 5 -UseBasicParsing
        $health = "OK $($r.StatusCode)"
    } catch { $health = "FAIL: $($_.Exception.Message)" }

    Write-Host "`n本地后端  (127.0.0.1:$LocalPort): $health"
    if ($state) {
        Write-Host "启动时间  : $($state.startedAt)"
        Write-Host "运行模式  : $($state.backendMode)"
        Write-Host "公网地址  : $($state.url)"
    } else {
        Write-Warn2 "无部署状态记录（可能未由本脚本启动）"
    }
    if (Test-Path $TunnelLog) {
        $last = Get-Content $TunnelLog -Tail 3
        Write-Host "隧道日志尾: `n$($last -join "`n")"
    }
}

if ($Stop) { Stop-All; exit 0 }
if ($Status) { Show-Status; exit 0 }

# =================================================================
# Step 1：准备 env
# =================================================================
if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Copy-Item $EnvExample $EnvFile
        Write-Warn2 "已从 .env.local.example 生成 $EnvFile（请按需修改 POSTGRES_PASSWORD / JWT_SECRET）"
    }
}

# =================================================================
# Step 2：启动后端（Docker 优先，uvicorn 兜底）
# =================================================================
function Wait-Health([int]$timeoutSec = 90) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:$LocalPort/health" -TimeoutSec 4 -UseBasicParsing
            if ($r.StatusCode -eq 200) { return $true }
        } catch { }
        Start-Sleep -Seconds 3
    }
    return $false
}

# 已在监听则直接复用
$existing = Get-NetTCPConnection -LocalPort $LocalPort -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    Write-Ok "端口 $LocalPort 已有服务在监听，复用现有后端"
    $backendMode = "reuse"
    $backendPid = ($existing | Select-Object -First 1).OwningProcess
} else {
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if ($docker -and (Test-Path $ComposeFile)) {
        Write-Step "用 Docker Compose 启动（docker-compose.local.yml）"
        $composeArgs = @("compose", "-f", $ComposeFile, "--env-file", $EnvFile, "up", "-d")
        if ($ForceRebuild) { $composeArgs += "--build" }
        & docker @composeArgs 2>&1 | Select-Object -Last 6
        if ($LASTEXITCODE -ne 0) { Write-Err2 "docker compose 启动失败"; exit 1 }
        $backendMode = "docker"
        $backendPid = $null
    } else {
        Write-Warn2 "未检测到 Docker，回退 uvicorn（SQLite dev 库）"
        $py = Join-Path $BackendDir ".venv\Scripts\python.exe"
        if (-not (Test-Path $py)) { $py = "python" }
        $uvArgs = @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$LocalPort")
        $p = Start-Process -FilePath $py -ArgumentList $uvArgs -WorkingDirectory $BackendDir `
            -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput $UvicornOut -RedirectStandardError $UvicornErr
        $backendMode = "uvicorn"
        $backendPid = $p.Id
        Write-Ok "uvicorn 已启动 (pid $($p.Id))，日志 $UvicornErr"
    }
}

Write-Step "等待健康检查 /health ..."
if (-not (Wait-Health 120)) {
    Write-Err2 "后端未在 120 秒内就绪，请查看 $UvicornErr（uvicorn 模式）或 docker logs"
    exit 1
}
Write-Ok "后端就绪：http://127.0.0.1:$LocalPort/health"

# =================================================================
# Step 3：隧道
# =================================================================
$tunnelPid = $null
$publicUrl = $null

if (-not $SkipTunnel -and $Provider -ne "none") {
    if ($Provider -eq "cloudflare") {
        $cf = $null
        foreach ($cand in @(
            (Join-Path "D:\ai\prj\trae\HuaWei\MyLangLean\.tools" "cloudflared.exe"),
            (Join-Path $env:USERPROFILE "cloudflared.exe")
        )) { if (Test-Path $cand) { $cf = $cand; break } }
        if (-not $cf) {
            $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
            if ($cmd) { $cf = $cmd.Source }
        }
        if (-not $cf) {
            Write-Err2 "未找到 cloudflared.exe。用镜像下载后重跑："
            Write-Host '  & "$env:SystemRoot\System32\curl.exe" -L -o D:\ai\prj\trae\HuaWei\MyLangLean\.tools\cloudflared.exe https://ghfast.top/https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe'
            exit 1
        }

        Write-Step "启动 Cloudflare 临时隧道（quick tunnel）"
        Remove-Item $TunnelLog -Force -ErrorAction SilentlyContinue
        $tArgs = @("tunnel", "--url", "http://127.0.0.1:$LocalPort", "--loglevel", "info",
                   "--logfile", $TunnelLog, "--no-autoupdate", "--protocol", "http2")
        $tp = Start-Process -FilePath $cf -ArgumentList $tArgs -WindowStyle Hidden -PassThru
        $tunnelPid = $tp.Id

        Write-Step "等待隧道分配公网地址（最长 120 秒）"
        $deadline = (Get-Date).AddSeconds(120)
        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Seconds 3
            if (Test-Path $TunnelLog) {
                $m = Select-String -Path $TunnelLog -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -AllMatches |
                     Select-Object -First 1
                if ($m) { $publicUrl = $m.Matches[0].Value; break }
            }
            if ($tp.HasExited) { Write-Err2 "cloudflared 提前退出，日志：$TunnelLog"; exit 1 }
        }
        if (-not $publicUrl) {
            Write-Err2 "未能解析出公网地址，日志：$TunnelLog"
            exit 1
        }
        Write-Ok "公网地址：$publicUrl"
    }
    elseif ($Provider -eq "cpolar") {
        $cmd = Get-Command cpolar -ErrorAction SilentlyContinue
        if (-not $cmd) { Write-Err2 "未安装 cpolar；国内网络访问 Cloudflare 不畅时再启用此分支"; exit 1 }
        Write-Step "启动 cpolar（需已配置 authtoken）"
        $cp = Start-Process -FilePath $cmd.Source -ArgumentList @("http", "-region", "cn_vip", "$LocalPort") `
            -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $LogDir "cpolar.out.log")
        $tunnelPid = $cp.Id
        Write-Warn2 "cpolar 地址需在 https://www.cpolar.com/status 查看（本脚本不解析）"
    }
}

# =================================================================
# Step 4：公网链路自检（仅云端可达时）
# =================================================================
if ($publicUrl) {
    Write-Step "经 Cloudflare 回环验证（最多 90 秒，首次 SSL 握手可能较慢）"
    $ok = $false
    for ($i = 0; $i -lt 10; $i++) {
        try {
            $r = Invoke-WebRequest -Uri "$publicUrl/health" -TimeoutSec 15 -UseBasicParsing
            if ($r.StatusCode -eq 200) { Write-Ok "公网 /health => 200 $($r.Content)"; $ok = $true; break }
        } catch {
            $msg = $_.Exception.Message
            Write-Warn2 "第 $($i+1) 次探测失败：$($msg.Substring(0, [Math]::Min(80, $msg.Length)))"
        }
        Start-Sleep -Seconds 8
    }
    if (-not $ok) {
        Write-Warn2 "公网自检未通过。常见原因：大陆网络访问 trycloudflare.com 受阻、或本机出网被限制。"
        Write-Warn2 "备选：换 cpolar 国内节点（-Provider cpolar）；或直接用阿里云 ECS 做反向隧道。"
    }
}

# =================================================================
# Step 5：写状态
# =================================================================
@{
    backendMode = $backendMode
    backendPid  = $backendPid
    tunnelPid   = $tunnelPid
    url         = $publicUrl
    port        = $LocalPort
    startedAt   = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    provider    = $Provider
} | ConvertTo-Json | Set-Content -Path $StateFile -Encoding utf8

Write-Host ""
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor DarkGray
Write-Host " 本地部署完成" -ForegroundColor Green
Write-Host " 后端      : http://127.0.0.1:$LocalPort  ($backendMode)"
if ($publicUrl) { Write-Host " 公网地址  : $publicUrl" }
Write-Host " 状态文件  : $StateFile"
Write-Host " 停止      : pwsh scripts/local-deploy.ps1 -Stop"
Write-Host ""
Write-Host " 真机联调（EBG-AN00）："
Write-Host "   1) App 登录 → 我的 → 环境诊断 → 服务地址填上面公网地址（不带结尾 /）"
Write-Host "   2) 保存后回首页，验证登录/试卷列表/听力播放"
Write-Host "   注：trycloudflare 地址每次重启会变，长期验证请用命名隧道 + 自有域名"
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor DarkGray
