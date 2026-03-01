#!/bin/bash

# ==========================================
# Script: gitnexus-wiki.sh
# Description: 异步生成 GitNexus Wiki，支持全套大模型参数的层级提取与持久化
# ==========================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PID_FILE=".gitnexus/wiki.pid"
LOG_FILE=".gitnexus/wiki.log"
GITNEXUS_GLOBAL_DIR="$HOME/.gitnexus"
GITNEXUS_GLOBAL_CONFIG="$GITNEXUS_GLOBAL_DIR/config.json"

echo -e "${GREEN}📖 [GitNexus Wiki Skill] 开始生成任务...${NC}"

# 环境检查
if ! command -v node &> /dev/null || ! command -v gitnexus &> /dev/null; then
    echo -e "${RED}❌ 错误: 未检测到 Node.js 或 gitnexus。${NC}"
    exit 1
fi

if [ ! -d ".gitnexus" ]; then
    echo -e "${RED}❌ 错误: 未找到 .gitnexus 索引。请先构建图谱。${NC}"
    exit 1
fi

# 保存用户提供的新配置
if [ -n "$API_KEY" ] || [ -n "$BASE_URL" ] || [ -n "$MODEL" ]; then
    echo -e "${YELLOW}💾 保存新配置至全局文件...${NC}"
    mkdir -p "$GITNEXUS_GLOBAL_DIR"
    node -e "
    const fs = require('fs');
    let config = {};
    if (fs.existsSync('$GITNEXUS_GLOBAL_CONFIG')) {
        try { config = JSON.parse(fs.readFileSync('$GITNEXUS_GLOBAL_CONFIG', 'utf8')); } catch(e){}
    }
    if ('$API_KEY') config.apiKey = '$API_KEY';
    if ('$BASE_URL') config.baseUrl = '$BASE_URL';
    if ('$MODEL') config.model = '$MODEL';
    fs.writeFileSync('$GITNEXUS_GLOBAL_CONFIG', JSON.stringify(config, null, 2));
    "
fi

# 读取大模型配置参数
echo -e "${YELLOW}🔍 读取大模型配置参数...${NC}"
export EXTRACTED_CONFIG=$(node -e "
const fs = require('fs'); const os = require('os'); const path = require('path');
const homeDir = os.homedir();
const paths = {
    gitnexus: [path.join(homeDir, '.gitnexus', 'config.json')],
    opencode: [path.join(homeDir, '.config', 'opencode', 'opencode.json')],
    claude:   [path.join(homeDir, '.claude', 'settings.json')]
};
function extractConfig(filePath, type) {
    if (fs.existsSync(filePath)) {
        try {
            const config = JSON.parse(fs.readFileSync(filePath, 'utf8'));
            
            // Claude 配置格式
            if (type === 'claude' && config.env) {
                const apiKey = config.env.ANTHROPIC_AUTH_TOKEN || config.env.ANTHROPIC_API_KEY || '';
                const baseUrl = config.env.ANTHROPIC_BASE_URL || '';
                const model = config.env.ANTHROPIC_MODEL || '';
                if (apiKey) return { apiKey, baseUrl, model };
            }
            
            // Opencode 配置格式
            if (type === 'opencode' && config.provider) {
                // 获取第一个 provider
                const providerKeys = Object.keys(config.provider);
                if (providerKeys.length > 0) {
                    const firstProviderKey = providerKeys[0];
                    const providerConfig = config.provider[firstProviderKey];
                    const apiKey = providerConfig.options?.apiKey || '';
                    const baseUrl = providerConfig.options?.baseURL || '';
                    // 从 models 中获取第一个模型的 key 作为默认模型
                    let model = '';
                    if (providerConfig.models && Object.keys(providerConfig.models).length > 0) {
                        model = Object.keys(providerConfig.models)[0];
                    }
                    if (apiKey) return { apiKey, baseUrl, model };
                }
            }
            
            // 通用配置格式
            const apiKey = config.apiKey || config.ANTHROPIC_API_KEY || config.OPENAI_API_KEY || config.primaryApiKey || '';
            const baseUrl = config.baseUrl || config.apiBase || config.endpoint || config.baseURL || '';
            const model = config.model || config.modelName || config.primaryModel || '';
            if (apiKey) return { apiKey, baseUrl, model };
        } catch (e) {}
    }
    return null;
}
let result = null;
for (let p of paths.gitnexus) { result = extractConfig(p, 'gitnexus'); if (result) break; }
if (!result) { for (let p of paths.opencode) { result = extractConfig(p, 'opencode'); if (result) break; } }
if (!result) { for (let p of paths.claude) { result = extractConfig(p, 'claude'); if (result) break; } }

if (result && result.apiKey) {
    console.log((result.apiKey || '') + '|' + (result.baseUrl || '') + '|' + (result.model || ''));
} else { console.log('NOT_FOUND||'); }
")

IFS='|' read -r EXTRACTED_API_KEY EXTRACTED_BASE_URL EXTRACTED_MODEL <<< "$EXTRACTED_CONFIG"

# 检查是否找到配置
if [ "$EXTRACTED_API_KEY" == "NOT_FOUND" ] || [ -z "$EXTRACTED_API_KEY" ]; then
    echo -e "${RED}❌ [ACTION_REQUIRED] 未找到大模型 API Key。${NC}"
    exit 2
fi

echo -e "${GREEN}✅ 成功读取大模型参数。${NC}"

# 构建命令参数
CMD_ARGS=""
if [ -n "$EXTRACTED_API_KEY" ]; then CMD_ARGS="$CMD_ARGS --api-key $EXTRACTED_API_KEY"; fi
if [ -n "$EXTRACTED_BASE_URL" ]; then CMD_ARGS="$CMD_ARGS --base-url $EXTRACTED_BASE_URL"; fi
if [ -n "$EXTRACTED_MODEL" ]; then CMD_ARGS="$CMD_ARGS --model $EXTRACTED_MODEL"; fi

# 进程防抖：终止旧进程
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    kill -9 $OLD_PID > /dev/null 2>&1 || true
fi

# 后台启动 Wiki 生成
nohup gitnexus wiki $CMD_ARGS > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

# 输出结果
echo -e "\n${GREEN}==========================================${NC}"
echo -e "${GREEN}🚀 Wiki 生成任务已后台运行！${NC}"
echo -e "🔍 进度命令：${GREEN}tail -f $LOG_FILE${NC}"
echo -e "${GREEN}==========================================${NC}\n"
