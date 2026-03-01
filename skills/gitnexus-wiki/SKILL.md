---
name: "gitnexus-wiki"
description: "使用 GitNexus 调用大语言模型生成项目架构 Wiki。当用户要求生成文档、创建项目 Wiki 或编写架构文档时调用。"
---

# GitNexus Wiki 生成器 Skill

## 技能描述

此技能用于同步调用 GitNexus 为当前代码库生成架构 Wiki。

该脚本会在当前终端实时输出进度。生成完毕后，它会自动在后台无缝恢复 `gitnexus serve` 进程，并跨平台唤醒系统默认浏览器，打开官方 Web UI 供用户查看图谱与产物。

### 工具超时中断 (Timeout) 处理
如果遇到超时，请不要直接向用户报错失败，而是按照以下步骤排查并安抚用户：

1. **主动在后台执行进程检查**：
   ```bash
   ps -ef | grep "gitnexus wiki" | grep -v grep
   ```

2. **主动检查目录下的 HTML 文件**：
   ```bash
   find . -maxdepth 2 -name "*.html" -type f 2>/dev/null | head -5
   ```

3. **向用户汇报**：
   > "大模型生成耗时较长超出了我的等待时间。经检查，[后台进程还在运行/已生成了HTML文件]。您可以手动运行 `./scripts/gitnexus-wiki.sh` 实时查看进度，脚本跑完会自动帮您在浏览器中打开 UI。"

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
ls -la *.md 2>/dev/null | grep -i wiki || ls -la .gitnexus/*.md 2>/dev/null | grep -i wiki || echo "NO_WIKI_FILE"
```

#### 情况 A：进程正在运行
如果检测到 `gitnexus wiki` 进程正在运行，告诉用户：
> "检测到 Wiki 生成任务正在进行中，请稍候。您可以使用 `ps aux | grep gitnexus` 查看进程状态。"

#### 情况 B：Wiki 文件已存在且进程未运行
如果检测到 Wiki 文件（如 `WIKI.md`、`wiki.md` 或 `.gitnexus/*.md`）且没有运行中的进程，询问用户：
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
如果脚本返回成功（exit code 0），执行以下检查命令确认 Wiki 文件：
```bash
find . -maxdepth 2 -name "*wiki*.md" -o -name "*Wiki*.md" -o -name "WIKI.md" 2>/dev/null | head -5
```
然后告诉用户：
> "✅ Wiki 生成任务已完成！生成的 Wiki 文件位于：[显示找到的文件路径]。Web UI 已在浏览器中打开，您可以查看完整的代码图谱。"

#### 情况 B：执行超时或中断
如果脚本执行超时或被中断，**立即执行以下检查命令**：

**检查进程状态**：
```bash
ps -ef | grep "gitnexus wiki" | grep -v grep
```

**检查 HTML 文件生成情况**：
```bash
find . -maxdepth 2 -name "*.html" -type f 2>/dev/null | head -5
```

根据检查结果，向用户汇报：
- 如果进程还在运行：
  > "大模型生成耗时较长超出了我的等待时间。经检查，后台进程还在运行中。您可以手动运行 `./scripts/gitnexus-wiki.sh` 实时查看进度，脚本跑完会自动帮您在浏览器中打开 UI。"

- 如果已生成 HTML 文件：
  > "大模型生成耗时较长超出了我的等待时间。经检查，已生成了 HTML 文件。您可以手动运行 `./scripts/gitnexus-wiki.sh` 完成剩余步骤，脚本跑完会自动帮您在浏览器中打开 UI。"

- 如果无进程且无文件：
  > "由于代码库较大，等待大模型生成超时了，您可以直接在终端手动运行 `./scripts/gitnexus-wiki.sh` 来查看完整实时进度。"

#### 情况 C：缺少配置（脚本输出包含 `[ACTION_REQUIRED]`）
**不要报错结束**。主动询问用户：
> "我没有在您的本地配置中找到大模型 API Key。请直接发送您的 API Key 给我。如果您使用自定义代理或特定模型，也可以一并告诉我（如：Key + 代理地址 + 模型名），我将为您全局保存并继续生成。"

#### 情况 D：用户提供 API Key 后
当用户提供 API Key、Base URL、模型名等信息后，**必须执行以下命令**：
```bash
API_KEY="用户提供的Key" BASE_URL="用户提供的URL" MODEL="用户提供的模型" ./scripts/gitnexus-wiki.sh
```

## 状态检查命令参考

### 检查 Wiki 生成进程
```bash
ps aux | grep -E "gitnexus wiki" | grep -v grep
```

### 查找已生成的 Wiki 文件
```bash
find . -maxdepth 2 -type f \( -iname "*wiki*.md" -o -iname "WIKI.md" \) 2>/dev/null
```

### 检查 HTML 产物文件
```bash
find . -maxdepth 2 -name "*.html" -type f 2>/dev/null | head -5
```

### 检查最近修改的 Markdown 文件
```bash
ls -lt *.md .gitnexus/*.md 2>/dev/null | head -10
```

## 核心能力

1. **智能层级读取**：按优先级读取多个配置源
2. **OpenCode Provider 支持**：自动从 OpenCode 配置的第一个 provider 中提取 API Key、Base URL 和模型
3. **Claude Settings 支持**：从 Claude Code 的 settings.json 中提取配置
4. **全局持久化**：新配置保存到 `~/.gitnexus/config.json`
5. **进程防抖**：杀掉旧的 wiki 进程，避免冲突
6. **同步执行**：前台生成文档，实时显示进度
7. **多模型支持**：支持 OpenAI、Anthropic 等兼容接口
8. **状态检测**：自动检测现有 Wiki 生成状态和文件
9. **自动恢复 Web UI**：生成完成后自动启动 `gitnexus serve`
10. **跨平台浏览器唤醒**：自动打开官方 Web UI 查看图谱

## 配置层级（优先级从高到低）

1. **环境变量**：`API_KEY`, `BASE_URL`, `MODEL`
2. **GitNexus 全局配置**：`~/.gitnexus/config.json`
3. **OpenCode 配置**：`~/.config/opencode/opencode.json`
4. **Claude Code 配置**：`~/.claude/settings.json`

## 预期输出

执行成功后，向用户展示：
- Wiki 文件生成位置（通过 `find` 命令定位）
- 文件大小和修改时间（通过 `ls -lh` 查看）
- Web UI 已在浏览器中打开的确认信息

## 质量评估标准

1. **配置发现**：成功从所有配置源读取
2. **全局持久化**：新配置正确保存
3. **进程防抖**：旧进程终止后才启动新进程
4. **状态检测**：正确识别现有 Wiki 生成状态和文件
5. **超时处理**：超时后主动检查进程和文件状态，给出准确反馈
6. **自动恢复**：生成完成后自动启动 Web UI 服务
7. **浏览器唤醒**：成功跨平台打开浏览器访问图谱
8. **优雅降级**：配置缺失时给出清晰提示

## 参考资料

详见 [Reference.md](./Reference.md)
