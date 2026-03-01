#!/bin/bash

# ==========================================
# Script: gitnexus-setup.sh
# Description: 自动化安装、配置 GitNexus、注入 Hook 并静默启动 Web UI (含异步与进程防抖)
# ==========================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SERVE_PORT=54321
PID_FILE=".gitnexus/analyze.pid"

echo -e "${GREEN}🚀 [GitNexus Setup Skill] 开始环境检查与自动化部署...${NC}"

# 环境检查
if ! command -v git &> /dev/null || ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ 错误: 需要 Git 和 npm 环境，请先安装。${NC}"
    exit 1
fi

if ! git rev-parse --is-inside-work-tree &> /dev/null; then
    echo -e "${RED}❌ 错误: 当前目录不是 Git 仓库。${NC}"
    exit 1
fi

mkdir -p .gitnexus

# 全局安装
if ! command -v gitnexus &> /dev/null; then
    echo -e "${YELLOW}📦 正在全局自动安装 gitnexus...${NC}"
    npm install -g gitnexus
else
    echo -e "${GREEN}✅ GitNexus 已全局安装。${NC}"
fi

# 异步图谱构建
echo -e "${YELLOW}🔍 正在后台异步分析代码库...${NC}"
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    kill -9 $OLD_PID > /dev/null 2>&1 || true
fi
nohup gitnexus analyze > .gitnexus/analyze.log 2>&1 &
echo $! > "$PID_FILE"

# MCP 配置注入
echo -e "${YELLOW}⚙️ 正在为当前项目注入 MCP 配置...${NC}"
gitnexus setup

# Post-commit 钩子配置
HOOK_DIR=".git/hooks"
HOOK_FILE="$HOOK_DIR/post-commit"
echo -e "${YELLOW}🪝 配置后台自动更新钩子 (post-commit)...${NC}"
mkdir -p "$HOOK_DIR"

cat << 'EOF' > "$HOOK_FILE"
#!/bin/sh
PID_FILE=".gitnexus/analyze.pid"
echo "🔄 [GitNexus] 检测到新提交，准备后台更新知识图谱..."
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    kill -9 $OLD_PID > /dev/null 2>&1 || true
fi
nohup npx gitnexus analyze > .gitnexus/analyze.log 2>&1 &
echo $! > "$PID_FILE"
EOF

chmod +x "$HOOK_FILE"
echo -e "${GREEN}✅ post-commit 钩子配置完成。${NC}"

# 清理旧进程
echo -e "${YELLOW}🧹 扫描并清理已存在的 Web UI 进程...${NC}"
pkill -f "gitnexus serve" > /dev/null 2>&1 || true
sleep 1

# 启动 Web UI
echo -e "${YELLOW}🌐 正在后台静默启动 Web UI 服务 (端口: ${SERVE_PORT})...${NC}"
nohup env PORT=${SERVE_PORT} gitnexus serve --port ${SERVE_PORT} > .gitnexus/serve.log 2>&1 &
sleep 2

# 输出结果
echo -e "\n${GREEN}==========================================${NC}"
echo -e "${GREEN}🎉 GitNexus 环境已就绪！${NC}"
echo -e "${GREEN}==========================================${NC}"
echo -e "🔗 ${YELLOW}Web UI 访问地址:${NC}"
echo -e "   📍 本地直连 : http://localhost:${SERVE_PORT}"
echo -e "   🌍 官方云端 : https://gitnexus.vercel.app/?server=http://localhost:${SERVE_PORT}"
echo -e "💡 提示: 索引正在后台建立。运行 ${GREEN}cat .gitnexus/analyze.log${NC} 查看进度。"
echo -e "${GREEN}==========================================${NC}\n"
