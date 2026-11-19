#!/usr/bin/env bash
# =================================================================
# AiLearning —— 独立 ECS 初始化（Ubuntu 24.04，root 执行）
#
# 做四件事：swap / 时区 / Docker CE（阿里云源 + 镜像加速）/ 基础安全
# 参考 RetroEmuPouch tools/account_backend/scripts/setup-ecs.sh，
# 并补上它缺的三项：2G swap + swappiness、时区、fail2ban。
#
# 用法（在服务器上，仓库已 clone 到 /opt/ailearning-backend）：
#   bash scripts/setup-ailearning-ecs.sh
#
# 注意：阿里云安全组需手工放通 22/80/443，ufw 挡不住 Docker 发布的端口。
# =================================================================
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "❌ 请用 root 执行"
  exit 1
fi

echo "=================================================="
echo "  AiLearning ECS 初始化"
echo "=================================================="

# ── 1. swap（2G）──
if swapon --show | grep -q '/swapfile'; then
  echo "✅ swap 已存在：$(swapon --show | tail -1)"
else
  echo "📦 创建 2G swap ..."
  if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
  fi
  swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  echo "✅ swap 已启用"
fi

# 低内存机器不要过于激进地换出
if grep -q '^vm.swappiness' /etc/sysctl.conf; then
  sed -i 's/^vm.swappiness.*/vm.swappiness=10/' /etc/sysctl.conf
else
  echo 'vm.swappiness=10' >> /etc/sysctl.conf
fi
sysctl -p >/dev/null
echo "✅ vm.swappiness=$(cat /proc/sys/vm/swappiness)"

# ── 2. 时区 ──
timedatectl set-timezone Asia/Shanghai
echo "✅ 时区：$(timedatectl show -p Timezone --value)"

# ── 3. Docker CE（阿里云源）──
if command -v docker >/dev/null 2>&1; then
  echo "✅ Docker 已安装：$(docker --version)"
else
  echo "📦 安装 Docker CE（阿里云镜像站）..."
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL --retry 3 https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  CODENAME="$(. /etc/os-release && echo "$VERSION_CODENAME")"
  ARCH="$(dpkg --print-architecture)"
  if ! curl -fsSL --max-time 15 \
      "https://mirrors.aliyun.com/docker-ce/linux/ubuntu/dists/${CODENAME}/Release" -o /dev/null; then
    echo "⚠️  镜像站无 ${CODENAME}，回退 jammy"
    CODENAME="jammy"
  fi
  echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.asc] https://mirrors.aliyun.com/docker-ce/linux/ubuntu ${CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
  echo "✅ Docker 安装完成"
fi

docker compose version >/dev/null 2>&1 || { echo "❌ compose v2 不可用"; exit 1; }
echo "✅ $(docker compose version)"

# 镜像加速（大陆直连 registry-1.docker.io 会超时）
mkdir -p /etc/docker
if ! grep -q 'registry-mirrors' /etc/docker/daemon.json 2>/dev/null; then
  printf '%s\n' '{"registry-mirrors":["https://docker.m.daocloud.io","https://docker.1ms.run","https://hub.rat.dev"]}' \
    > /etc/docker/daemon.json
  systemctl restart docker
  echo "✅ 已配置 Docker Hub 镜像加速"
fi

# ── 4. 基础工具与安全 ──
apt-get install -y -qq git rsync htop unzip fail2ban >/dev/null
systemctl enable --now fail2ban >/dev/null 2>&1 || true
echo "✅ 基础工具与 fail2ban 就绪"

if command -v ufw >/dev/null 2>&1; then
  ufw allow 22/tcp  >/dev/null 2>&1 || true
  ufw allow 80/tcp  >/dev/null 2>&1 || true
  ufw allow 443/tcp >/dev/null 2>&1 || true
  echo "✅ ufw 已放通 22/80/443（仍需在阿里云安全组放通）"
fi

PUBLIC_IP=$(curl -s --max-time 5 ifconfig.me || echo unknown)

cat <<EOF

==================================================
  ✅ 初始化完成
  公网 IP : ${PUBLIC_IP}
  时区    : $(timedatectl show -p Timezone --value)
  swap    : $(swapon --show | tail -1)
  Docker  : $(docker --version)

  接下来：
    1) 阿里云控制台 → 安全组 → 入方向放通 22 / 80 / 443
    2) cp deploy/.env.example deploy/.env && 填 POSTGRES_PASSWORD / JWT_SECRET
    3) 备案前：docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.staging.yml up -d --build
       备案后：docker compose -f deploy/docker-compose.yml up -d --build
    4) 音频：rsync -av --partial .../question_audio/ /opt/ailearning-assets/question_audio/
==================================================
EOF
