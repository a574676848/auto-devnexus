# 快速入门指南

本指南将帮助你在 5 分钟内开始使用 Auto-GitNexus。

## 目录

- [环境准备](#环境准备)
- [安装](#安装)
- [基础使用](#基础使用)
- [故障排除](#故障排除)

## 环境准备

### 系统要求

- **操作系统**: macOS, Linux, Windows (WSL)
- **Git**: >= 2.0
- **Node.js**: >= 16
- **npm**: >= 8

### 验证环境

```bash
# 检查 Git
git --version

# 检查 Node.js
node --version

# 检查 npm
npm --version
```

## 安装

### 1. 克隆仓库

```bash
git clone git@github.com:a574676848/auto-gitnexus.git
cd auto-gitnexus
```

### 2. 设置执行权限

```bash
chmod +x skills/*/scripts/*.sh
```

## 基础使用

### 方式一：通过 AI 助手调用（推荐）

如果你使用 Claude Code 或 OpenCode 等支持 MCP 的 AI 助手，可以直接说出：

#### 初始化 GitNexus

> "初始化 GitNexus 环境"

AI 助手将自动执行以下操作：
1. 检查环境依赖
2. 全局安装 gitnexus（如未安装）
3. 分析代码库生成图谱
4. 注入 MCP 配置
5. 配置 post-commit 钩子
6. 启动 Web UI 服务

#### 生成项目 Wiki

> "使用 GitNexus 帮我生成项目架构 Wiki"

AI 助手将：
1. 读取 LLM 配置
2. 异步生成项目文档
3. 保存到 `.gitnexus/wiki/` 目录

### 方式二：手动执行

#### 初始化 GitNexus

```bash
./skills/gitnexus-setup/scripts/gitnexus-setup.sh
```

预期输出：
```
🚀 [GitNexus Setup Skill] 开始环境检查与自动化部署...
✅ GitNexus 已全局安装。
🔍 正在后台异步分析代码库...
⚙️ 正在为当前项目注入 MCP 配置...
🪝 配置后台自动更新钩子 (post-commit)...
🧹 扫描并清理已存在的 Web UI 进程...
🌐 正在后台静默启动 Web UI 服务 (端口: 54321)...

==========================================
🎉 GitNexus 环境已就绪！
==========================================
🔗 Web UI 访问地址:
   📍 本地直连 : http://localhost:54321
   🌍 官方云端 : https://gitnexus.vercel.app/?server=http://localhost:54321
💡 提示: 索引正在后台建立。运行 cat .gitnexus/analyze.log 查看进度。
==========================================
```

#### 生成 Wiki

```bash
./skills/gitnexus-wiki/scripts/gitnexus-wiki.sh
```

如果缺少 LLM 配置，脚本会提示你提供：
```
[ACTION_REQUIRED] 未找到 LLM 配置。请提供 API Key。
```

你可以通过环境变量传入：
```bash
API_KEY="your-api-key" BASE_URL="https://api.openai.com/v1" MODEL="gpt-4" ./skills/gitnexus-wiki/scripts/gitnexus-wiki.sh
```

## 故障排除

### 权限被拒绝

**问题**: `Permission denied` 错误

**解决**:
```bash
chmod +x skills/*/scripts/*.sh
```

### GitNexus 未安装

**问题**: `gitnexus: command not found`

**解决**:
```bash
npm install -g gitnexus
```

### 端口被占用

**问题**: Web UI 无法启动，端口 54321 被占用

**解决**:
```bash
# 查找占用端口的进程
lsof -i :54321

# 杀掉进程
kill -9 <PID>

# 重新运行脚本
./skills/gitnexus-setup/scripts/gitnexus-setup.sh
```

### 缺少 LLM 配置

**问题**: Wiki 生成时提示缺少 API Key

**解决**:

1. 创建全局配置文件：
```bash
mkdir -p ~/.gitnexus
cat > ~/.gitnexus/config.json << EOF
{
  "apiKey": "your-api-key",
  "baseUrl": "https://api.openai.com/v1",
  "model": "gpt-4"
}
EOF
```

2. 或在 OpenCode/Claude Code 中配置好 LLM

### 图谱分析失败

**问题**: `.gitnexus/` 目录未生成或为空

**解决**:
```bash
# 手动运行分析
gitnexus analyze

# 查看错误日志
cat .gitnexus/analyze.log
```

---

## 下一步

- 阅读 [Skill 详细文档](../skills/gitnexus-setup/README.md)
- 了解 [贡献指南](../CONTRIBUTING.md)
- 探索 [GitNexus 官方文档](https://github.com/abhigyanpatwari/GitNexus)
