# =================================================================
# AiLearning —— 独立 ECS 部署脚本（参考 RetroEmuPouch deploy.ps1 的 action 风格）
#
# 与旧方案的区别：不做 scp 大目录（backend/ 887 MB 在 3 Mbps 下约 40 分钟且不可续传），
# 改为「服务器 git clone/pull + 服务器构建」（仓库 46 MB，约 2 分钟）。
#
# 用法：
#   $env:AIL_ECS_HOST='<新实例公网IP>'
#   $env:AIL_ECS_KEY='C:\Users\liuzhixing\.ssh\<key>'
#   pwsh scripts/deploy-backend.ps1 -Action setup      # 首次：clone + 初始化（swap/时区/Docker）
#   pwsh scripts/deploy-backend.ps1 -Action deploy      # 构建并启动（默认 prod）
#   pwsh scripts/deploy-backend.ps1 -Action deploy -Staging   # 备案前纯 HTTP
#   pwsh scripts/deploy-backend.ps1 -Action seed
#   pwsh scripts/deploy-backend.ps1 -Action status
#   pwsh scripts/deploy-backend.ps1 -Action logs
#   pwsh scripts/deploy-backend.ps1 -Action stop
#   pwsh scripts/deploy-backend.ps1 -Action assets      # 同步 1.7 GB 音频（慢，建议 OSS）
#
# 说明：本脚本尚未在独立实例上实测（当前仅完成本地阶段 0 验证）。
# =================================================================
param(
    [ValidateSet("setup", "deploy", "seed", "status", "logs", "stop", "assets")]
    [string]$Action = "deploy",
    [switch]$Staging,
    [string]$HostName = $env:AIL_ECS_HOST,
    [string]$User = "root",
    [string]$Key = $(if ($env:AIL_ECS_KEY) { $env:AIL_ECS_KEY } else { "C:\Users\liuzhixing\.ssh\id_ecs99" }),
    [string]$AppDir = "/opt/ailearning-backend",
    [string]$Repo = "https://github.com/chihinglau/AiLearning.git",
    [string]$AssetsDir = "/opt/ailearning-assets",
    [string]$LocalAudio = "D:\ai\prj\trae\HuaWei\AiLearning\backend\build\question_audio"
)

$ErrorActionPreference = "Stop"
$SshExe = "C:\Windows\System32\OpenSSH\ssh.exe"
$ScpExe = "C:\Windows\System32\OpenSSH\scp.exe"

if (-not (Test-Path $SshExe)) { Write-Host "❌ 未找到 ssh.exe：$SshExe" -ForegroundColor Red; exit 1 }
if (-not $HostName) { Write-Host "❌ 请先设置 `$env:AIL_ECS_HOST`（新实例公网 IP）" -ForegroundColor Red; exit 1 }
if (-not (Test-Path $Key)) { Write-Host "❌ SSH 私钥不存在：$Key" -ForegroundColor Red; exit 1 }

function Invoke-Remote {
    param([string]$Script, [switch]$Quiet)
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Script))
    $cmd = "echo $b64 | base64 -d | bash"
    if ($Quiet) {
        & $SshExe -i $Key -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 "$User@$HostName" $cmd 2>&1 | Out-Null
    } else {
        & $SshExe -i $Key -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 "$User@$HostName" $cmd 2>&1
    }
}

$ComposeFiles = if ($Staging) {
    "-f deploy/docker-compose.yml -f deploy/docker-compose.staging.yml"
} else {
    "-f deploy/docker-compose.yml"
}

switch ($Action) {
    "setup" {
        Write-Host "▶ 首次初始化：clone 仓库 + swap/时区/Docker" -ForegroundColor Cyan
        Invoke-Remote @"
set -e
mkdir -p '$AppDir'
if [ ! -d '$AppDir/.git' ]; then
  git clone '$Repo' '$AppDir'
else
  cd '$AppDir' && git fetch --all && git reset --hard origin/main
fi
cd '$AppDir'
bash scripts/setup-ailearning-ecs.sh
"@
        Write-Host ""
        Write-Host "下一步：在服务器上 cp deploy/.env.example deploy/.env 并填 POSTGRES_PASSWORD / JWT_SECRET" -ForegroundColor Yellow
    }

    "deploy" {
        Write-Host "▶ 拉代码并构建（Staging=$Staging）" -ForegroundColor Cyan
        Invoke-Remote @"
set -e
cd '$AppDir'
git fetch --all && git reset --hard origin/main
if [ ! -f deploy/.env ]; then echo '❌ 缺少 deploy/.env'; exit 1; fi
docker compose $ComposeFiles build
docker compose $ComposeFiles up -d
sleep 8
docker compose $ComposeFiles ps
"@
    }

    "seed" {
        Write-Host "▶ 灌入底座内容（RUN_SEED 之外的手动触发）" -ForegroundColor Cyan
        Invoke-Remote "cd '$AppDir' && docker compose $ComposeFiles exec -T api python -m scripts.seed"
    }

    "status" {
        Write-Host "▶ 状态检查" -ForegroundColor Cyan
        Invoke-Remote @"
cd '$AppDir'
docker compose $ComposeFiles ps
echo '--- health ---'
curl -fsS http://127.0.0.1:8000/health 2>/dev/null || \
  docker compose $ComposeFiles exec -T api curl -fsS http://127.0.0.1:8000/health
echo '--- disk ---'
df -h / | tail -1
free -m | head -3
"@
    }

    "logs" {
        Invoke-Remote "cd '$AppDir' && docker compose $ComposeFiles logs --tail 100 api"
    }

    "stop" {
        Write-Host "▶ 停止栈" -ForegroundColor Cyan
        Invoke-Remote "cd '$AppDir' && docker compose $ComposeFiles down"
    }

    "assets" {
        Write-Host "▶ 同步音频资产（约 1.7 GB；3 Mbps 约 78 分钟，建议改用 OSS+CDN）" -ForegroundColor Yellow
        if (-not (Test-Path $LocalAudio)) { Write-Host "❌ 本地音频目录不存在：$LocalAudio" -ForegroundColor Red; exit 1 }
        Invoke-Remote "mkdir -p '$AssetsDir/question_audio'" | Out-Null
        & $ScpExe -r -i $Key -o StrictHostKeyChecking=accept-new "$LocalAudio/*" "$User@$HostName`:$AssetsDir/question_audio/"
        Write-Host "✅ 同步完成；确认 deploy/.env 或 compose 的 ASSETS_DIR=$AssetsDir" -ForegroundColor Green
    }
}
