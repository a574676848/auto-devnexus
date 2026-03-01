#!/bin/bash

# ==========================================
# Script: gitnexus-setup.sh
# Description: 自动化安装、注入 Hook 并静默启动 Web UI (含 KùzuDB 强力防死锁与自动恢复)
# ==========================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SERVE_PORT=54321
PID_FILE=".gitnexus/analyze.pid"

echo -e "${GREEN}🚀 [GitNexus Setup Skill] 开始环境检查与自动化部署...${NC}"

if ! command -v git &> /dev/null || ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ 错误: 需要 Git 和 npm 环境。${NC}"
    exit 1
fi
if ! git rev-parse --is-inside-work-tree &> /dev/null; then
    echo -e "${RED}❌ 错误: 当前目录不是 Git 仓库。${NC}"
    exit 1
fi

mkdir -p .gitnexus

if ! command -v gitnexus &> /dev/null; then
    echo -e "${YELLOW}📦 正在全局自动安装 gitnexus...${NC}"
    npm install -g gitnexus
fi

# ==========================================
# 🛑 [核心防御] 释放所有 KùzuDB 数据库锁
# ==========================================
echo -e "${YELLOW}🧹 正在释放 KùzuDB 数据库锁 (清理旧进程)...${NC}"
pkill -f "gitnexus serve" > /dev/null 2>&1 || true
pkill -f "gitnexus analyze" > /dev/null 2>&1 || true
pkill -f "gitnexus wiki" > /dev/null 2>&1 || true
sleep 1

echo -e "${YELLOW}🔍 正在后台异步分析代码库...${NC}"
nohup gitnexus analyze > .gitnexus/analyze.log 2>&1 &
echo $! > "$PID_FILE"

echo -e "${YELLOW}⚙️ 正在为当前项目注入 MCP 配置...${NC}"
gitnexus setup

HOOK_DIR=".git/hooks"
HOOK_FILE="$HOOK_DIR/post-commit"
echo -e "${YELLOW}🪝 配置后台自动更新钩子 (支持死锁防御与 UI 自动恢复)...${NC}"
mkdir -p "$HOOK_DIR"
cat << EOF > "$HOOK_FILE"
#!/bin/sh
echo "🔄 [GitNexus] 检测到新提交，准备后台更新知识图谱..."

# 将清场、分析、恢复三个动作包装成一个按顺序执行的后台队列
nohup sh -c '
    # 1. 强制释放数据库写锁
    pkill -f "gitnexus serve" > /dev/null 2>&1 || true
    pkill -f "gitnexus analyze" > /dev/null 2>&1 || true
    sleep 1
    
    # 2. 独占锁生成索引
    npx gitnexus analyze > .gitnexus/analyze.log 2>&1
    
    # 3. 释放锁后，自动拉起 Web UI 服务
    nohup env PORT=${SERVE_PORT} npx gitnexus serve --port ${SERVE_PORT} > .gitnexus/serve.log 2>&1 &
' > /dev/null 2>&1 &
EOF
chmod +x "$HOOK_FILE"
echo -e "${GREEN}✅ post-commit 钩子配置完成。${NC}"

echo -e "${YELLOW}🌐 正在后台静默启动 Web UI 服务 (端口: ${SERVE_PORT})...${NC}"
nohup env PORT=${SERVE_PORT} gitnexus serve --port ${SERVE_PORT} > .gitnexus/serve.log 2>&1 &

echo -e "\n${GREEN}==========================================${NC}"
echo -e "${GREEN}🎉 GitNexus 环境已就绪！${NC}"
echo -e "${GREEN}==========================================${NC}"
echo -e "🔗 ${YELLOW}Web UI 访问地址:${NC}"
echo -e "   📍 本地直连 : http://localhost:${SERVE_PORT}"
echo -e "   🌍 官方云端 : https://gitnexus.vercel.app/?server=http://localhost:${SERVE_PORT}"
echo -e "💡 提示: 索引正在后台建立。运行 ${GREEN}cat .gitnexus/analyze.log${NC} 查看进度。"
echo -e "${GREEN}==========================================${NC}\n"
