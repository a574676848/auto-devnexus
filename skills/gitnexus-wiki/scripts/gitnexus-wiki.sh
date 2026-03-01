#!/bin/bash

# ==========================================
# Script: gitnexus-wiki.sh
# Description: 同步生成 GitNexus Wiki，支持中文 Prompt 注入及实时终端输出
# ==========================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SERVE_PORT=54321
GITNEXUS_GLOBAL_DIR="$HOME/.gitnexus"
GITNEXUS_GLOBAL_CONFIG="$GITNEXUS_GLOBAL_DIR/config.json"

echo -e "${GREEN}📖 [GitNexus Wiki Skill] 开始生成任务与环境检测...${NC}"

if ! command -v node &> /dev/null || ! command -v gitnexus &> /dev/null; then
    echo -e "${RED}❌ 错误: 未检测到 Node.js 或 gitnexus。${NC}"
    exit 1
fi
if [ ! -d ".gitnexus" ]; then
    echo -e "${RED}❌ 错误: 未找到本地 .gitnexus 索引。${NC}"
    exit 1
fi

echo -e "${YELLOW}🇨🇳 正在检查并为源码注入【强制中文输出】指令...${NC}"
node -e "
const fs = require('fs'); const path = require('path'); const { execSync } = require('child_process');
try {
    const root = execSync('npm root -g').toString().trim();
    const pkgPath = path.join(root, 'gitnexus');
    if (!fs.existsSync(pkgPath)) process.exit(0);
    const cnInstruction = ' \\\\nIMPORTANT: You MUST generate the entire wiki, including all headings, explanations, and summaries, strictly in Simplified Chinese (简体中文). Do NOT use English unless for code variables.';
    function patchDir(dir) {
        for (const f of fs.readdirSync(dir)) {
            const fullPath = path.join(dir, f);
            if (fs.statSync(fullPath).isDirectory()) patchDir(fullPath);
            else if (fullPath.endsWith('.js')) {
                let code = fs.readFileSync(fullPath, 'utf8');
                if (code.includes('Simplified Chinese')) continue;
                let patched = false;
                code = code.replace(/(['\"\`])([^'\"\`]*?(?:generate|create|write)[^'\"\`]*?wiki[^'\"\`]*?)\1/gi, (m, q, c) => { patched = true; return q + c + cnInstruction + q; });
                code = code.replace(/(role:\\s*['\"\`]system['\"\`]\\s*,\\s*content:\\s*['\"\`])(.*?)(['\"\`])/g, (m, p, c, s) => { patched = true; return p + c + cnInstruction + s; });
                if (patched) fs.writeFileSync(fullPath, code, 'utf8');
            }
        }
    }
    ['dist', 'src', 'bin', 'lib'].forEach(subDir => {
        const targetDir = path.join(pkgPath, subDir);
        if (fs.existsSync(targetDir)) patchDir(targetDir);
    });
} catch(e) {}
"

if [ -n "$API_KEY" ] || [ -n "$BASE_URL" ] || [ -n "$MODEL" ]; then
    echo -e "${YELLOW}💾 保存新配置至全局文件...${NC}"
    mkdir -p "$GITNEXUS_GLOBAL_DIR"
    node -e "
    const fs = require('fs'); let config = {};
    if (fs.existsSync('$GITNEXUS_GLOBAL_CONFIG')) { try { config = JSON.parse(fs.readFileSync('$GITNEXUS_GLOBAL_CONFIG', 'utf8')); } catch(e){} }
    if ('$API_KEY') config.apiKey = '$API_KEY'; if ('$BASE_URL') config.baseUrl = '$BASE_URL'; if ('$MODEL') config.model = '$MODEL';
    fs.writeFileSync('$GITNEXUS_GLOBAL_CONFIG', JSON.stringify(config, null, 2));
    "
fi

echo -e "${YELLOW}🔍 读取大模型配置参数...${NC}"
export EXTRACTED_CONFIG=$(node -e "
const fs = require('fs'); const os = require('os'); const path = require('path');
const homeDir = os.homedir();
const paths = {
    gitnexus: [path.join(homeDir, '.gitnexus', 'config.json')],
    opencode: [path.join(homeDir, '.opencode.json'), path.join(homeDir, '.config', 'opencode', 'config.json')],
    claude:   [path.join(homeDir, '.claude.json'), path.join(homeDir, '.config', 'claude', 'config.json')]
};
function extractConfig(filePath) {
    if (fs.existsSync(filePath)) {
        try {
            const config = JSON.parse(fs.readFileSync(filePath, 'utf8'));
            const apiKey = config.apiKey || config.ANTHROPIC_API_KEY || config.OPENAI_API_KEY || config.primaryApiKey || '';
            const baseUrl = config.baseUrl || config.apiBase || config.endpoint || config.baseURL || '';
            const model = config.model || config.modelName || config.primaryModel || '';
            if (apiKey) return { apiKey, baseUrl, model };
        } catch (e) {}
    }
    return null;
}
let result = null;
for (let p of paths.gitnexus) { result = extractConfig(p); if (result) break; }
if (!result) { for (let p of paths.opencode) { result = extractConfig(p); if (result) break; } }
if (!result) { for (let p of paths.claude) { result = extractConfig(p); if (result) break; } }
if (result && result.apiKey) console.log((result.apiKey || '') + '|' + (result.baseUrl || '') + '|' + (result.model || ''));
else console.log('NOT_FOUND||');
")

IFS='|' read -r EXTRACTED_API_KEY EXTRACTED_BASE_URL EXTRACTED_MODEL <<< "$EXTRACTED_CONFIG"

if [ "$EXTRACTED_API_KEY" == "NOT_FOUND" ] || [ -z "$EXTRACTED_API_KEY" ]; then
    echo -e "${RED}❌ [ACTION_REQUIRED] 未找到大模型 API Key。${NC}"
    exit 2
fi

export OPENAI_API_KEY="$EXTRACTED_API_KEY"
export ANTHROPIC_API_KEY="$EXTRACTED_API_KEY"

CMD_ARGS=""
if [ -n "$EXTRACTED_BASE_URL" ]; then CMD_ARGS="$CMD_ARGS --base-url $EXTRACTED_BASE_URL"; fi
if [ -n "$EXTRACTED_MODEL" ]; then CMD_ARGS="$CMD_ARGS --model $EXTRACTED_MODEL"; fi

# ==========================================
# 🛑 强制清空 KùzuDB 文件锁
# ==========================================
echo -e "${YELLOW}🧹 正在解除 KùzuDB 数据库占用锁...${NC}"
pkill -f "gitnexus serve" > /dev/null 2>&1 || true
pkill -f "gitnexus analyze" > /dev/null 2>&1 || true
pkill -f "gitnexus wiki" > /dev/null 2>&1 || true
sleep 1

echo -e "\n${GREEN}==========================================${NC}"
echo -e "${GREEN}🚀 开始同步生成中文 Wiki，请在此窗口查看实时进度...${NC}"
echo -e "${GREEN}==========================================${NC}\n"

# 1. 同步执行 Wiki 生成
gitnexus wiki $CMD_ARGS

# 2. 生成完毕后，立即在后台恢复 Web UI 服务
echo -e "\n${YELLOW}🌐 正在后台恢复 Web UI 服务 (端口: ${SERVE_PORT})...${NC}"
nohup env PORT=${SERVE_PORT} gitnexus serve --port ${SERVE_PORT} > .gitnexus/serve.log 2>&1 &
sleep 2

# 3. 拼装官方 Web UI 桥接地址
UI_URL="https://gitnexus.vercel.app/?server=http://localhost:${SERVE_PORT}"

echo -e "${GREEN}🌍 正在自动为您在浏览器中打开 Web UI 及生成的图谱...${NC}"

# 4. 跨平台唤醒浏览器
OS="$(uname -s)"
case "${OS}" in
    Darwin*)
        # macOS
        open "${UI_URL}"
        ;;
    Linux*)
        # Linux
        if command -v xdg-open &> /dev/null; then
            xdg-open "${UI_URL}"
        else
            echo -e "   📍 自动打开失败，请手动访问: ${UI_URL}"
        fi
        ;;
    CYGWIN*|MINGW*|MSYS*)
        # Windows (Git Bash)
        start "${UI_URL}"
        ;;
    *)
        echo -e "   📍 请手动访问: ${UI_URL}"
        ;;
esac

echo -e "\n${GREEN}==========================================${NC}"
echo -e "${GREEN}✅ Wiki 生成任务与环境恢复已全部完成！${NC}"
echo -e "${GREEN}==========================================${NC}"
echo -e ""
echo -e "📚 ${YELLOW}常用命令:${NC}"
echo -e "   ${GREEN}gitnexus list${NC}        - 查看所有已索引的仓库列表"
echo -e "   ${GREEN}gitnexus status${NC}       - 查看当前仓库的索引状态"
echo -e "   ${GREEN}gitnexus wiki --help${NC}  - 查看 Wiki 生成帮助"
echo -e "${GREEN}==========================================${NC}\n"
