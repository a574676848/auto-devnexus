---
name: "gitnexus-wiki"
description: "使用 GitNexus 调用大语言模型生成项目架构 Wiki。当用户要求生成文档、创建项目 Wiki 或编写架构文档时调用。"
---

# GitNexus Wiki 生成器 Skill

## 技能描述

此技能用于异步调用 GitNexus 为当前代码库生成架构 Wiki。

该脚本会在后台异步生成 Wiki 文档，生成完成后用户可以直接在浏览器中打开 `.gitnexus/wiki/index.html` 查看结果。

**重要提示**：所有输出和交互必须使用中文（简体中文）。

## 触发条件

当用户说出以下关键词时调用此 Skill：
- "生成 Wiki"
- "创建文档"
- "写项目文档"
- "生成架构文档"
- "用 GitNexus 写文档"
- "Wiki 生成进度"
- "查看 Wiki 状态"

## 执行步骤（必须按顺序执行）

### 步骤 1：检查现有 Wiki 生成状态
**首先执行以下命令检查是否已有 Wiki 在生成或已完成**：
```bash
ps aux | grep -E "gitnexus wiki" | grep -v grep && echo "RUNNING" || echo "NOT_RUNNING"
```

同时检查 Wiki 文件是否已存在：
```bash
ls -lh .gitnexus/wiki/index.html 2>/dev/null && echo "WIKI_EXISTS" || echo "NO_WIKI_FILE"
```

#### 情况 A：进程正在运行
如果检测到 `gitnexus wiki` 进程正在运行，告诉用户：
> "检测到 Wiki 生成任务正在进行中。生成完成后，您可以在浏览器中打开 `.gitnexus/wiki/index.html` 查看结果。"

#### 情况 B：Wiki 文件已存在且进程未运行
如果检测到 Wiki 文件（`.gitnexus/wiki/index.html`）且没有运行中的进程，询问用户：
> "检测到已有 Wiki 文件生成。您想要：1) 查看现有 Wiki；2) 重新生成 Wiki；3) 查看 Wiki 文件位置？"

#### 情况 C：无运行进程且无 Wiki 文件
继续执行步骤 2。

### 步骤 2：执行 Wiki 生成脚本
**必须立即执行以下命令**：
```bash
./scripts/gitnexus-wiki.sh
```

### 步骤 3：处理权限错误（如需要）
如果步骤 2 返回 "Permission denied" 错误，**必须先执行赋权命令**：
```bash
chmod +x ./scripts/gitnexus-wiki.sh
```
然后**重新执行步骤 2**。

### 步骤 4：处理执行结果

根据脚本的返回结果，按以下情况处理：

#### 情况 A：执行成功
如果脚本返回成功（exit code 0），告诉用户：
> "✅ Wiki 生成任务已在后台启动！生成完成后，您可以在浏览器中打开 `.gitnexus/wiki/index.html` 查看结果。"

#### 情况 B：缺少配置（脚本输出包含 `[ACTION_REQUIRED]`）
**不要报错结束**。主动询问用户：
> "我没有在您的本地配置中找到大模型 API Key。请直接发送您的 API Key 给我。如果您使用自定义代理或特定模型，也可以一并告诉我（如：Key + 代理地址 + 模型名），我将为您全局保存并继续生成。"

#### 情况 C：用户提供 API Key 后
当用户提供 API Key、Base URL、模型名等信息后，**必须执行以下命令**：
```bash
API_KEY="用户提供的Key" BASE_URL="用户提供的URL" MODEL="用户提供的模型" ./scripts/gitnexus-wiki.sh
```

## 状态检查命令参考

### 检查 Wiki 生成进程
```bash
ps aux | grep -E "gitnexus wiki" | grep -v grep
```

### 检查 Wiki 文件是否已生成
```bash
ls -lh .gitnexus/wiki/index.html 2>/dev/null || echo "Wiki 仍在生成中..."
```

### 查看 Wiki 生成日志
```bash
cat .gitnexus/wiki.log
```

### 查找已生成的 Wiki 文件
```bash
find . -maxdepth 2 -type f \( -iname "*wiki*.md" -o -iname "WIKI.md" \) 2>/dev/null
```

## 常用命令（中文说明）

```bash
# 查看所有已索引的仓库列表
gitnexus list

# 查看当前仓库的索引状态
gitnexus status

# 查看 Wiki 生成帮助
gitnexus wiki --help
```

## 核心能力

1. **智能层级读取**：按优先级读取多个配置源
2. **OpenCode Provider 支持**：自动从 OpenCode 配置的第一个 provider 中提取 API Key、Base URL 和模型
3. **Claude Settings 支持**：从 Claude Code 的 settings.json 中提取配置
4. **全局持久化**：新配置保存到 `~/.gitnexus/config.json`
5. **进程防抖**：杀掉旧的 wiki 进程，避免冲突
6. **异步执行**：后台生成文档，不阻塞用户操作
7. **多模型支持**：支持 OpenAI、Anthropic 等兼容接口
8. **状态检测**：自动检测现有 Wiki 生成状态和文件
9. **浏览器查看**：生成完成后可直接在浏览器中打开 `.gitnexus/wiki/index.html`
10. **中文输出**：所有提示和说明使用简体中文

## 配置层级（优先级从高到低）

1. **环境变量**：`API_KEY`, `BASE_URL`, `MODEL`
2. **GitNexus 全局配置**：`~/.gitnexus/config.json`
3. **OpenCode 配置**：`~/.config/opencode/opencode.json`
4. **Claude Code 配置**：`~/.claude/settings.json`

## 预期输出

执行成功后，向用户展示：
- Wiki 生成位置：`.gitnexus/wiki/index.html`
- 浏览器查看方式：`file://$(pwd)/.gitnexus/wiki/index.html`
- 检查进度命令：`ls -lh .gitnexus/wiki/index.html`
- 常用命令提示（中文说明）

## 质量评估标准

1. **配置发现**：成功从所有配置源读取
2. **全局持久化**：新配置正确保存
3. **进程防抖**：旧进程终止后才启动新进程
4. **状态检测**：正确识别现有 Wiki 生成状态和文件
5. **异步执行**：生成任务在后台运行，不阻塞用户
6. **优雅降级**：配置缺失时给出清晰提示
7. **中文输出**：所有提示和说明使用简体中文

## 参考资料

详见 [Reference.md](./Reference.md)
