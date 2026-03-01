# GitNexus Wiki 生成器 Skill

## 简介

本 Skill 用于异步调用 GitNexus 为当前代码库生成架构 Wiki。采用官方标准传参规范，拥有智能层级读取机制，支持按需索要 Key/BaseUrl/Model 并实现全局持久化，避免 Token 连点浪费。

**重要提示**：所有输出和交互必须使用中文（简体中文）。

## 功能特性

- **智能层级读取**：优先读取 `~/.gitnexus/config.json` → OpenCode 配置 → Claude Code 配置
- **全局持久化**：新配置保存到 `~/.gitnexus/config.json`，后续使用无需重复输入
- **进程防抖**：杀掉旧的 wiki 进程，避免资源冲突
- **异步执行**：后台生成文档，不阻塞用户操作
- **浏览器查看**：生成完成后可直接在浏览器中打开 `.gitnexus/wiki/index.html`
- **多模型支持**：支持 OpenAI、Anthropic 及兼容接口
- **中文输出**：所有提示和说明使用简体中文

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
5. **浏览器查看**：生成完成后在浏览器中打开 `.gitnexus/wiki/index.html`

## 常用命令

```bash
# 查看所有已索引的仓库列表
gitnexus list

# 查看当前仓库的索引状态
gitnexus status

# 查看 Wiki 生成帮助
gitnexus wiki --help

# 检查 Wiki 文件是否已生成
ls -lh .gitnexus/wiki/index.html 2>/dev/null || echo "Wiki 仍在生成中..."

# 查看 Wiki 生成日志
cat .gitnexus/wiki.log
```

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
✅ Wiki 生成任务已在后台启动！

📁 生成位置:
   .gitnexus/wiki/index.html

🌐 查看方式:
   直接在浏览器中打开: file:///path/to/project/.gitnexus/wiki/index.html

📊 检查进度:
   运行以下命令查看 index.html 是否已生成:
   ls -lh .gitnexus/wiki/index.html 2>/dev/null || echo 'Wiki 仍在生成中...'

📚 常用命令:
   gitnexus list        - 查看所有已索引的仓库列表
   gitnexus status       - 查看当前仓库的索引状态
   cat .gitnexus/wiki.log - 查看 Wiki 生成日志
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
