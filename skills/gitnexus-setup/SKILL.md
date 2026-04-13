---
name: "gitnexus-setup"
description: "自动化安装、配置 GitNexus，注入 MCP 配置、挂载 post-commit 钩子、启动守护进程。当用户要求初始化、配置或重置 GitNexus 环境时调用。注意：脚本在技能目录下，执行在当前项目目录下。"
---

# GitNexus 环境初始化 Skill

## 技能描述

此 Skill 用于在当前 Git 仓库中全自动化安装、配置和管理 GitNexus 的后台守护进程。具备幂等性（Idempotent）和进程防抖能力，确保 AI 上下文库和本地 Web UI 始终与最新代码保持同步。

**重要提示**：所有输出和交互必须使用中文（简体中文）。

## 触发条件

当用户说出以下关键词时调用此 Skill：
- "初始化 GitNexus"
- "配置 GitNexus"
- "设置 GitNexus"
- "启动 GitNexus"
- "重置 GitNexus 环境"
- "安装 GitNexus"

## 执行步骤（必须按顺序执行）

### 步骤 1：执行 Skill 脚本

**⚠️ 重要**：脚本位于 **技能目录**（SKILL.md 所在目录），但需要在 **执行目录**（当前项目目录）下运行。

首先确定技能目录的绝对路径，然后执行：

```bash
# 获取技能目录的绝对路径（根据实际安装位置调整）
SKILL_DIR="你的技能目录绝对路径"  # 例如 ~/.claude/skills/gitnexus-setup

# 在执行目录（当前项目根目录）下运行脚本，传入 --workdir 确保脚本在正确的目录操作
"${SKILL_DIR}/scripts/gitnexus-setup.sh" --workdir "$(pwd)"
```

**不要询问用户是否执行，直接运行上述命令。**

### 步骤 2：处理权限错误（如需要）
如果步骤 1 返回 "Permission denied" 错误，**必须先执行赋权命令**：
```bash
chmod +x "${SKILL_DIR}/scripts/gitnexus-setup.sh"
```
然后**重新执行步骤 1**。

### 步骤 3：验证执行结果
- 如果脚本返回成功（exit code 0）：向用户展示"预期输出"中的信息
- 如果脚本返回错误：根据错误信息提示用户

## 核心能力

1. **全局安装**：检测并安装 npm 包 `gitnexus`
2. **异步图谱构建**：运行 `gitnexus analyze` 生成 AST 索引
3. **MCP 注入**：运行 `gitnexus setup` 注册图谱检索工具
4. **自动同步钩子**：创建并赋权 `.git/hooks/post-commit` 实现静默更新（如已存在会先删除再创建）
5. **进程防抖**：杀掉旧的 `gitnexus serve`、`gitnexus analyze`、`gitnexus wiki` 进程

## 常用命令（中文说明）

```bash
# 查看所有已索引的仓库列表
gitnexus list

# 查看当前仓库的索引状态
gitnexus status

# 启动本地 HTTP 服务器，连接 Web UI 查看图谱
gitnexus serve
# ⚠️ 注意: serve 命令会锁定数据库，运行期间无法执行 analyze/wiki
```

## 预期输出

执行成功后，向用户展示：
- 查看索引进度命令：`cat .gitnexus/analyze.log`
- 常用命令提示（中文说明）
- `gitnexus serve` 命令的锁库警告

## 质量评估标准

1. **幂等性**：多次执行结果一致，不产生错误
2. **进程防抖**：启动新进程前终止旧进程
3. **后台执行**：分析任务异步运行，不阻塞用户
4. **钩子持久化**：post-commit 钩子能 survive 仓库操作
5. **错误处理**：对缺失前置条件给出清晰提示
6. **中文输出**：所有提示和说明使用简体中文

## Skill 文件位置说明

本 Skill 可能位于以下目录之一：
- `~/.claude/skills/` - Claude Code 技能目录
- `~/.config/opencode/skills/` - OpenCode 技能目录
- `~/.cc-switch/skills/` - CC-Switch 技能目录

### ⚠️ 技能目录 vs 执行目录（重要）

**技能目录（A）**：SKILL.md 和脚本所在的目录，即 `$(dirname "$SKILL_FILE")`。
**执行目录（B）**：当前用户工作目录（即当前 Git 仓库根目录）。

**脚本位于 A 目录，但需要在 B 目录执行。** 执行时必须使用 A 目录的脚本路径：

```bash
# 1. 先确定脚本的绝对路径（基于技能目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/scripts" && pwd)"  # A 目录的 scripts 路径

# 2. 在执行目录（B）下运行脚本，传入 --workdir
"${SCRIPT_DIR}/gitnexus-setup.sh" --workdir "$(pwd)"
```

如果无法通过 shell 变量解析脚本路径，请根据 Skill 的实际安装位置使用对应的绝对路径：
- `~/.claude/skills/gitnexus-setup/scripts/gitnexus-setup.sh --workdir "$(pwd)"`
- `~/.config/opencode/skills/gitnexus-setup/scripts/gitnexus-setup.sh --workdir "$(pwd)"`
- `~/.cc-switch/skills/gitnexus-setup/scripts/gitnexus-setup.sh --workdir "$(pwd)"`

## 参考资料

详见 [Reference.md](./Reference.md)
