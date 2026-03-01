# GitNexus Wiki 生成器 Skill

## 简介

本 Skill 用于异步调用 GitNexus 为当前代码库生成架构 Wiki。采用官方标准传参规范，拥有智能层级读取机制，支持按需索要 Key/BaseUrl/Model 并实现全局持久化，避免 Token 连点浪费。

## 功能特性

- **智能层级读取**：优先读取 `~/.gitnexus/config.json` → OpenCode 配置 → Claude Code 配置
- **全局持久化**：新配置保存到 `~/.gitnexus/config.json`，后续使用无需重复输入
- **进程防抖**：杀掉旧的 wiki 进程，避免资源冲突
- **异步执行**：后台生成文档，不阻塞用户操作
- **多模型支持**：支持 OpenAI、Anthropic 及兼容接口

## 目录结构

```
gitnexus-wiki/
├── SKILL.md              # Skill 主定义文件（AI 调用入口）
├── README.md             # 项目说明文档
├── Reference.md          # 官方命令与资源参考
└── scripts/
    └── gitnexus-wiki.sh  # 核心执行脚本
```

## 快速使用

对 AI 助手说：
> "使用 GitNexus 帮我生成项目架构 Wiki"

或

> "生成项目文档"

## 工作流程

1. **配置读取**：按优先级从多个来源读取 LLM 配置
2. **配置保存**：如用户提供新配置，保存到全局配置文件
3. **环境验证**：检查 GitNexus 是否已安装和初始化
4. **异步生成**：后台运行 `gitnexus wiki` 命令
5. **进度监控**：用户可通过日志文件查看生成进度

## 配置层级

配置按以下优先级读取（高优先级覆盖低优先级）：

| 优先级 | 配置源 | 字段名 |
|--------|--------|--------|
| 1 | 环境变量 | `API_KEY`, `BASE_URL`, `MODEL` |
| 2 | GitNexus 全局 | `~/.gitnexus/config.json` |
| 3 | OpenCode | `~/.opencode.json` 或 `~/.config/opencode/config.json` |
| 4 | Claude Code | `~/.claude.json` 或 `~/.config/claude/config.json` |

## 配置字段映射

| 标准字段 | 可能的字段名 |
|----------|--------------|
| API Key | `apiKey`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `primaryApiKey` |
| Base URL | `baseUrl`, `apiBase`, `endpoint`, `baseURL` |
| Model | `model`, `modelName`, `primaryModel` |

## 输出示例

```
🚀 Wiki 生成任务已后台运行！
========================================
🔍 进度命令：tail -f .gitnexus/wiki.log
========================================
```

## 依赖要求

- GitNexus 环境已初始化（`.gitnexus` 目录存在）
- Node.js 和 gitnexus CLI 已安装
- LLM API Key（OpenAI、Anthropic 或兼容）

## 相关 Skill

- [gitnexus-setup](../gitnexus-setup/) - 初始化 GitNexus 环境

## 许可证

遵循 GitNexus 官方许可证
