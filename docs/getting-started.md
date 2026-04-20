# 快速入门指南

本指南将帮助你在 5 分钟内开始使用 Auto-GitNexus。

## 目录

- [环境准备](#环境准备)
- [安装](#安装)
- [基础使用](#基础使用)
- [Windows WezTerm 脚本](#windows-wezterm-脚本)
- [故障排除](#故障排除)

## 环境准备

### 系统要求

- **操作系统**: macOS, Linux, Windows (WSL)
- **Git**: >= 2.0
- **Node.js**: >= 16 (仅 GitNexus 相关技能需要)
- **npm**: >= 8 (仅 GitNexus 相关技能需要)
- **Python**: >= 3.6 (仅 Jira 集成技能需要)
- **Windows PowerShell**: 建议 PowerShell 5.1+ 或 PowerShell 7（仅 WezTerm Windows 脚本需要）

### 验证环境

```bash
# 检查 Git
git --version

# 检查 Node.js (仅 GitNexus 相关技能需要)
node --version

# 检查 npm (仅 GitNexus 相关技能需要)
npm --version

# 检查 Python (仅 Jira 集成技能需要)
python --version 或 python3 --version
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

Windows 本机如需安装 WezTerm，可执行：

```powershell
.\scripts\windows\wezterm\install-wezterm.bat
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

#### Jira 工单操作

> "帮我在 Jira 创建一个工单"
> "查询 Jira 中我的待办工单"
> "更新 TEST-123 工单的状态"

AI 助手将：
1. 检查 Jira 配置（首次使用会提示输入）
2. 执行相应的工单操作
3. 更新记忆系统以优化后续操作

#### 解析仓库源码

> "帮我解析这个仓库 github.com/user/repo"
> "读取这个 GitLab 私有仓库的源码 https://gitlab.example.com/group/project"

AI 助手将：
1. 自动识别仓库类型（GitHub 或私有 Git）
2. 尝试获取访问凭证（集成配置 → 本地缓存 → 询问用户）
3. Clone 代码到执行目录并解析结构
4. 输出目录树和分块代码，供 AI 逐步阅读

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

#### Jira 集成操作

```bash
# 配置 Jira 连接信息
python skills/jira-integration/scripts_py/auth.py --domain "https://your-jira-domain.com" --user "your-username" --token "your-password-or-api-token"

# 查询工单
python skills/jira-integration/scripts_py/search.py --jql "assignee = currentUser() AND status = 'Open'"

# 获取工单详情
python skills/jira-integration/scripts_py/get_issue.py --issue "TEST-123"
```

#### 仓库解析

```bash
# 解析 GitHub 公开/私有仓库
python skills/repo-parser/scripts/parse_github.py https://github.com/user/repo --workdir "E:\temp\parse-target"

# 解析私有仓库（GitLab、Gitea 等）
python skills/repo-parser/scripts/parse_local_git.py https://gitlab.example.com/group/project --workdir "E:\temp\parse-target"
```

> ⚠️ **注意**：脚本位于技能目录（A），但 clone 和输出文件写入 `--workdir` 指定的执行目录（B），两者必须分离。
> 凭证缓存位于 `%USERPROFILE%\.repo-parser\credential_cache.json`，不会提交到 Git。

### Windows WezTerm 脚本

仓库内置了 Windows 下的 WezTerm 一键安装与配置重置脚本：

```powershell
.\scripts\windows\wezterm\install-wezterm.bat
```

该脚本会：

1. 检测 WezTerm 是否已安装。
2. 已安装时跳过安装，仅重置用户侧配置。
3. 未安装时优先使用 `winget`，失败后回退到 GitHub Release MSI 安装。
4. 自动生成 `%USERPROFILE%\.config\wezterm\wezterm.lua`。
5. 自动生成 `%USERPROFILE%\.wezterm_cleanup.bat`、`%USERPROFILE%\.wezterm_cleanup.ps1`、`%USERPROFILE%\.wezterm_img_handler.ps1`。
6. 覆盖旧配置前自动备份，并且只保留最近 5 份备份。

详细说明见 [Windows WezTerm 一键安装脚本](./windows-wezterm.md)。

## 故障排除

### 权限被拒绝

**问题**: `Permission denied` 错误

**解决**:
```bash
chmod +x skills/*/scripts/*.sh
```

### WezTerm 安装失败

**问题**: Windows 下执行 WezTerm 安装脚本失败

**解决**:

```powershell
# 手动执行 PowerShell 版本
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\wezterm\install-wezterm.ps1

# 如需强制重新下载安装
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\wezterm\install-wezterm.ps1 -ForceDownload
```

如果仍失败，请检查：

1. 当前系统是否能访问 GitHub Release。
2. 是否具有 MSI 安装权限。
3. `winget` 是否可用。
4. `C:\Program Files\PowerShell\7\pwsh.exe` 是否存在。

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

### Jira 认证失败

**问题**: 执行 Jira 操作时提示认证失败

**解决**:
```bash
# 重新配置 Jira 连接信息
python skills/jira-integration/scripts_py/auth.py --domain "https://your-jira-domain.com" --user "your-username" --token "your-password-or-api-token"
```

### Jira API 400 错误

**问题**: 执行 Jira 操作时返回 400 错误

**解决**:
- 检查 JSON payload 格式是否正确
- 参考 `skills/jira-integration/MEMORY.md` 中的模板
- 确保所有必填字段都已提供

---

## 下一步

- 阅读 [GitNexus Setup Skill 文档](../skills/gitnexus-setup/README.md)
- 阅读 [Jira 集成 Skill 文档](../skills/jira-integration/README.md)
- 阅读 [仓库解析 Skill 文档](../skills/repo-parser/SKILL.md)
- 阅读 [Windows WezTerm 脚本文档](./windows-wezterm.md)
- 了解 [贡献指南](../CONTRIBUTING.md)
- 探索 [GitNexus 官方文档](https://github.com/abhigyanpatwari/GitNexus)
