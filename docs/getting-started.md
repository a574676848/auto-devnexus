# 快速入门指南

本指南从零开始，带你走完「装好环境 → 第一次成功调用 → 接入一个真实服务」。全程大约 5 分钟，前三步不花任何钱、也不需要任何 Key。

## 目录

- [1. 环境准备](#1-环境准备)
- [2. 安装](#2-安装)
- [3. 第一次成功调用](#3-第一次成功调用)
- [4. 两种调用方式](#4-两种调用方式)
- [5. 接入第三方服务](#5-接入第三方服务)
- [6. Windows WezTerm 脚本](#6-windows-wezterm-脚本)
- [7. 故障排除](#7-故障排除)
- [下一步](#下一步)

---

## 1. 环境准备

### 系统要求

| 组件 | 版本 | 谁需要 |
|------|------|--------|
| Git | >= 2.0 | 全部 |
| Python | >= 3.6 | Jira 集成与全部本地服务脚本；除 Jira 外都用标准库，**不需要 pip 安装依赖** |
| Node.js | >= 16 | `gitnexus-setup`、`gitnexus-wiki`、`codebase-memory-mcp-setup`，以及飞猪官方 CLI |
| npm | >= 8 | 同上 |
| PowerShell | 5.1+ 或 7 | 仅 Windows 下的 WezTerm 脚本 |

操作系统：Windows、macOS、Linux 都可以；GitNexus 相关的 Shell 脚本在 Windows 上建议用 Git Bash 或 WSL。

### 验证环境

```bash
git --version
python --version     # Windows 上如果没这个命令，用 py --version
node --version
npm --version
```

`git` 与 `python` 必须有；`node` / `npm` 只在你要用 GitNexus 或飞猪时才需要。

---

## 2. 安装

### 克隆仓库

```bash
git clone git@github.com:a574676848/auto-devnexus.git
cd auto-devnexus
```

### 补执行权限（仅 Linux / macOS）

```bash
chmod +x skills/*/scripts/*.sh
```

Python 脚本不需要这一步，也不需要安装——直接 `python skills/<skill>/scripts/<script>.py --help` 就能看到子命令。

### 可选：安装外部 CLI

```bash
npm i -g gitnexus              # gitnexus-setup / gitnexus-wiki 依赖
npm i -g @fly-ai/flyai-cli     # fliggy 依赖
# memos 由 memos-cli 提供，装好后执行 memos auth status 验证
```

---

## 3. 第一次成功调用

先跑一条**不需要任何 Key**的命令，确认环境和脚本都正常：

```bash
python skills/rails/scripts/rail.py stations 厦门
```

能看到车站电报码列表，说明 Python、脚本路径、网络请求三条链路都通了。

再试一个纯本地查询：

```bash
python skills/rails/scripts/rail.py query 厦门北 杭州东 2026-11-05
```

会返回车次、时刻、历时与席别余票。首次运行会自动拉取约 200KB 的车站表并缓存到 `~/.rails/stations.js`。

---

## 4. 两种调用方式

### 方式一：通过 AI 助手调用（推荐）

对支持 Skill 的 AI 助手说人话即可，它会读取对应 `SKILL.md` 后自行拼参数：

> "初始化 GitNexus 环境"

助手会依次：检查依赖 → 全局安装 `gitnexus` → 后台分析代码库生成图谱 → 注入 MCP 配置 → 挂 `post-commit` 钩子 → 启动 54321 端口的 Web UI。

> "使用 GitNexus 帮我生成项目架构 Wiki"

助手会读取 LLM 配置、异步生成文档到 `.gitnexus/wiki/`。

> "帮我在 Jira 创建一个工单"
> "查询 Jira 中我的待办工单"
> "更新 TEST-123 工单的状态"

> "帮我解析这个仓库 github.com/user/repo"

助手会自动识别仓库类型（GitHub 或私有 Git），按「集成配置 → 本地缓存 → 询问你」三级策略取凭证，clone 后分块输出源码。

> "查一下厦门到杭州的余票"
> "把主卧的灯关掉"
> "我的快递到哪了"

### 方式二：手动执行

#### GitNexus 初始化

```bash
./skills/gitnexus-setup/scripts/gitnexus-setup.sh
```

预期输出：

```text
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

#### 生成架构 Wiki

```bash
./skills/gitnexus-wiki/scripts/gitnexus-wiki.sh
```

缺少 LLM 配置时脚本会打印 `[ACTION_REQUIRED] 未找到 LLM 配置。请提供 API Key.`，也可以直接用环境变量传入：

```bash
API_KEY="<key>" BASE_URL="https://api.openai.com/v1" MODEL="gpt-4" \
  ./skills/gitnexus-wiki/scripts/gitnexus-wiki.sh
```

#### Jira

```bash
# 首次配置连接信息
python skills/jira-integration/scripts_py/auth.py --domain "https://jira.example.com" --user "<账号>" --token "<密码或 API Token>"

# 查询与读取
python skills/jira-integration/scripts_py/search.py --jql "assignee = currentUser() AND status = 'Open'"
python skills/jira-integration/scripts_py/get_issue.py --issue "TEST-123"
```

#### 仓库解析

```bash
# GitHub 公开或私有仓库
python skills/repo-parser/scripts/parse_github.py https://github.com/user/repo --workdir ./parse-out

# GitLab / Gitea 等私有仓库
python skills/repo-parser/scripts/parse_local_git.py https://gitlab.example.com/group/project --workdir ./parse-out
```

> ⚠️ 脚本在技能目录，clone 与输出写在 `--workdir` 指定的执行目录，两者必须分离。凭证缓存位于 `%USERPROFILE%\.repo-parser\credential_cache.json`（Unix 下为 `~/.repo-parser/`），不会提交到 Git。

#### 其他

每个脚本的完整子命令见对应 `SKILL.md`；接入类服务见 [local-services.md](local-services.md)。

---

## 5. 接入第三方服务

接入类 Skill 需要你先去官方控制台拿 Key。统一流程：

1. 在 [local-services.md](local-services.md) 找到目标服务章节
2. 按「申请」一栏去官方页面拿 Key 或授权码
3. 写到该章节指定的凭据文件或环境变量
4. 用章节里的第一条命令验证

凭据不会进仓库，也不会被脚本打印到日志里。

---

## 6. Windows WezTerm 脚本

仓库内置 Windows 下 WezTerm 的一键安装与配置重置脚本：

```powershell
.\scripts\windows\wezterm\install-wezterm.bat
```

该脚本会：

1. 检测 WezTerm 是否已安装
2. 已安装时跳过安装，仅重置用户侧配置
3. 未安装时优先用 `winget`，失败后回退 GitHub Release MSI
4. 生成 `%USERPROFILE%\.config\wezterm\wezterm.lua`
5. 生成 `%USERPROFILE%\.wezterm_cleanup.bat`、`.wezterm_cleanup.ps1`、`.wezterm_img_handler.ps1`
6. 覆盖旧配置前自动备份，只保留最近 5 份

详细说明见 [windows-wezterm.md](windows-wezterm.md)。

---

## 7. 故障排除

### 权限被拒绝

**现象**：`Permission denied`

**处理**（Linux / macOS）：

```bash
chmod +x skills/*/scripts/*.sh
```

Python 脚本不需要执行权限，用 `python <脚本>` 调用即可。

### 找不到 python 命令

**现象**：`python: command not found`

**处理**：Windows 上改用 `py`；或把 Python 加入 PATH。脚本按需使用绝对路径时，替换命令中的 `python` 即可。

### WezTerm 安装失败

**现象**：Windows 下执行 bat 失败

**处理**：

```powershell
# 手动执行 PowerShell 版本
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\wezterm\install-wezterm.ps1

# 强制重新下载安装
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\wezterm\install-wezterm.ps1 -ForceDownload
```

仍失败时检查：能否访问 GitHub Release、是否有 MSI 安装权限、`winget` 是否可用、`C:\Program Files\PowerShell\7\pwsh.exe` 是否存在。

### GitNexus 未安装

**现象**：`gitnexus: command not found`

```bash
npm install -g gitnexus
```

### 端口被占用

**现象**：Web UI 起不来，54321 被占用

```bash
# 查找占用进程
lsof -i :54321

# 杀掉
kill -9 <PID>

# 重跑
./skills/gitnexus-setup/scripts/gitnexus-setup.sh
```

Windows 上用 `netstat -ano | findstr :54321` 查 PID，再 `taskkill /PID <PID> /F`。

### 缺少 LLM 配置

**现象**：生成 Wiki 时提示缺少 API Key

**处理一**：写全局配置

```bash
mkdir -p ~/.gitnexus
cat > ~/.gitnexus/config.json <<'EOF'
{
  "apiKey": "<key>",
  "baseUrl": "https://api.openai.com/v1",
  "model": "gpt-4"
}
EOF
```

**处理二**：在 OpenCode / Claude Code 里配好 LLM，脚本会复用。

### 图谱分析失败

**现象**：`.gitnexus/` 目录没生成或为空

```bash
# 手动跑一次分析
gitnexus analyze

# 看日志
cat .gitnexus/analyze.log
```

### 第三方服务 401 / 403 / Key 无效

按顺序排查：环境变量是否设了空值覆盖了文件内容、凭据文件是否有多余空白或引号、Key 是否绑定了正确的服务类型（高德要选「Web 服务」，Cloudflare Token 要含对应 Zone 的 DNS 权限）、Token 是否过期（百度网盘执行 `bdpan.py refresh`）。逐服务细节见 [local-services.md](local-services.md)。

### AI 助手不触发某个 Skill

**现象**：说了需求，助手没加载对应 Skill

**处理**：换用该 Skill `SKILL.md` frontmatter 里 `description` 覆盖的说法，例如「瑞幸」「取餐码」能触发 `my-coffee`，而「帮我买杯咖啡」不一定。触发词写不进去时，直接把 Skill 名字告诉助手。

### Jira 认证失败

```bash
python skills/jira-integration/scripts_py/auth.py --domain "https://jira.example.com" --user "<账号>" --token "<密码或 Token>"
```

### Jira 接口返回 400

- 检查 JSON payload 格式
- 参考 `skills/jira-integration/MEMORY.md` 里的模板
- 确认必填字段齐全

---

## 下一步

- 想接第三方服务：[local-services.md](local-services.md)
- 想写自己的 Skill：[skill-specification.md](skill-specification.md)
- 想参与贡献：[../CONTRIBUTING.md](../CONTRIBUTING.md)
- 全部能力清单：[../README.md](../README.md)
- GitNexus 官方文档：<https://github.com/abhigyanpatwari/GitNexus>
