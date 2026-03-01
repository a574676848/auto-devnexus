---
name: "gitnexus-wiki"
description: "使用 GitNexus 调用大语言模型生成项目架构 Wiki。当用户要求生成文档、创建项目 Wiki 或编写架构文档时调用。"
---

# GitNexus Wiki 生成器 Skill

## 技能描述

此 Skill 用于异步调用 GitNexus 为当前代码库生成架构 Wiki。采用官方标准传参规范，拥有智能层级读取机制（优先读取 `~/.gitnexus/config.json` → OpenCode 配置 → Claude Code 配置）。如果全部未命中，将请求用户提供并全局持久化。

## 触发条件

当用户说出以下关键词时调用此 Skill：
- "生成 Wiki"
- "创建文档"
- "写项目文档"
- "生成架构文档"
- "用 GitNexus 写文档"

## 执行步骤

### 1. 执行脚本
直接执行脚本：
```bash
./scripts/gitnexus-wiki.sh
```

### 2. 错误处理
如果遇到 "Permission denied" 错误，先执行赋权命令：
```bash
chmod +x ./scripts/gitnexus-wiki.sh
```
然后重新执行脚本。

### 3. 处理返回结果

#### 情况 A：执行成功
如果脚本成功运行，告诉用户任务已在后台执行，并给出查看进度命令：
> "Wiki 生成任务已在后台运行，请使用 `tail -f .gitnexus/wiki.log` 查看进度。"

#### 情况 B：缺少配置（包含 `[ACTION_REQUIRED]`）
**不要报错结束**。主动询问用户：
> "我没有在您的本地配置中找到大模型 API Key。请直接发送您的 API Key 给我。如果您使用自定义代理或特定模型，也可以一并告诉我（如：Key + 代理地址 + 模型名），我将为您全局保存并继续生成。"

#### 情况 C：用户提供参数后
当用户提供 API Key 等信息后，将数据作为环境变量传入并再次执行：
```bash
API_KEY="用户Key" BASE_URL="用户URL" MODEL="用户模型" ./scripts/gitnexus-wiki.sh
```

## 核心能力

1. **智能层级读取**：按优先级读取多个配置源
2. **OpenCode Provider 支持**：自动从 OpenCode 配置的第一个 provider 中提取 API Key、Base URL 和模型
3. **Claude Settings 支持**：从 Claude Code 的 settings.json 中提取配置
4. **全局持久化**：新配置保存到 `~/.gitnexus/config.json`
5. **进程防抖**：杀掉旧的 wiki 进程，避免冲突
6. **异步执行**：后台生成文档，不阻塞用户
7. **多模型支持**：支持 OpenAI、Anthropic 等兼容接口

## 配置层级（优先级从高到低）

1. **环境变量**：`API_KEY`, `BASE_URL`, `MODEL`
2. **GitNexus 全局配置**：`~/.gitnexus/config.json`
3. **OpenCode 配置**：`~/.config/opencode/opencode.json`
4. **Claude Code 配置**：`~/.claude/settings.json`

## 预期输出

执行成功后，向用户展示：
- 监控进度命令：`tail -f .gitnexus/wiki.log`
- Wiki 文件生成位置（通常在项目根目录或 `.gitnexus/`）

## 质量评估标准

1. **配置发现**：成功从所有配置源读取
2. **全局持久化**：新配置正确保存
3. **进程防抖**：旧进程终止后才启动新进程
4. **后台执行**：生成任务异步运行
5. **进度可见**：用户可通过日志监控进度
6. **优雅降级**：配置缺失时给出清晰提示

## 参考资料

详见 [Reference.md](./Reference.md)
